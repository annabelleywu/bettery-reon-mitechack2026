"""When to bypass and when to put cells back: an adjustable control policy.

The challenge brief lets us assume switching and selective bypass: any cell can
be included in or removed from the active string, subject to system limits,
and we choose when. The system limit modelled here is the inverter's voltage
window: at most ``PackConfig.bypass_headroom`` (k) cells out of the string at
once. Every decision uses MEASURED signals only (``reon_model.monitoring``).

Actions, each switchable:

* ``bypass_on_empty``: during a discharge, a cell that empties drops out and the
  string runs on (uses the headroom left over).
* ``bypass_on_fault``: a faulted cell is bypassed instead of stopping the string.
  The pack is serviced only when bypassed cells exceed k.
* ``isolate_if``: proactively take a cell out for good when a measured feature
  crosses its threshold (e.g. ``{"soh_gap": 0.05}``), or when the learned fault
  model predicts a rate above ``{"predicted_fault_rate": 0.02}`` per year.
* ``rest_count`` / ``rest_by``: each step, rest the cells ranked highest by a
  feature (bypassed for that step, back in the string the next). Resting saves
  cycle aging but gives up that step's capacity.
* ``spare_for_faults``: headroom slots that isolation and resting may not use,
  kept free so a fault can still be bypassed.

``ControlPolicy.conventional()`` switches all of it off: the hardware then
behaves like a fixed series string (tested).
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass, field

import numpy as np


@dataclass
class ControlPolicy:
    bypass_on_empty: bool = True
    bypass_on_fault: bool = True
    isolate_if: dict = field(default_factory=dict)
    rest_count: int = 0
    rest_by: str = "soh_gap"             # a measured feature, or "remaining_life" (see RemainingLifeTracker)
    rest_threshold: float = 0.10         # remaining_life: rest if life < (1 - threshold) x pack median
    rest_stop_health: float = 0.0        # rest only while measured pack mean capacity is above this (0 = always)
    rest_temp_C: float = 0.0             # >0: also rest cells measured this much hotter than the pack mean
    spare_for_faults: int = 1
    risk_model: object | None = None      # a fitted PoissonIntensityGLM with feature_names

    @classmethod
    def conventional(cls) -> "ControlPolicy":
        return cls(bypass_on_empty=False, bypass_on_fault=False)

    # ------------------------------------------------------------------ helpers
    def _column(self, X, names, key):
        if key == "predicted_fault_rate":
            if self.risk_model is None:
                raise ValueError("predicted_fault_rate needs a fitted risk_model")
            cols = [names.index(f) for f in self.risk_model.feature_names]
            flat = X.reshape(-1, X.shape[-1])[:, cols]
            return self.risk_model.predict_rate(flat).reshape(X.shape[:-1])
        if key not in names:
            raise ValueError(f"feature {key!r} is not measured under this MonitoringConfig ({names})")
        return X[..., names.index(key)]

    @staticmethod
    def _pick(score, eligible, n_allowed):
        """Per pack, the up-to-n_allowed eligible cells with the highest score."""
        s = np.where(eligible, score, -np.inf)
        order = np.argsort(-s, axis=1)
        rank = np.empty_like(order)
        np.put_along_axis(rank, order, np.arange(s.shape[1])[None, :].repeat(s.shape[0], 0), axis=1)
        return eligible & (rank < np.maximum(n_allowed, 0)[:, None])

    # ---------------------------------------------------------------- decisions
    def isolate(self, X, names, in_string, headroom_left) -> np.ndarray:
        """Cells to take out for good this step."""
        if not self.isolate_if:
            return np.zeros(in_string.shape, dtype=bool)
        ratio = np.full(in_string.shape, -np.inf)
        for key, thr in self.isolate_if.items():
            ratio = np.maximum(ratio, self._column(X, names, key) / thr)
        return self._pick(ratio, in_string & (ratio > 1.0), headroom_left - self.spare_for_faults)

    def rest_by_life(self, life, in_string, headroom_left, pack_health) -> np.ndarray:
        """Rest the cells predicted to reach retirement first (lowest remaining life), if their
        life is more than ``rest_threshold`` below the pack median, while the pack is healthy."""
        if self.rest_count <= 0:
            return np.zeros(in_string.shape, dtype=bool)
        L = np.where(in_string & np.isfinite(life), life, np.nan)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)       # packs with no estimate yet
            med = np.nanmedian(L, axis=1, keepdims=True)
        eligible = np.isfinite(L) & (L < (1.0 - self.rest_threshold) * med)
        eligible &= (pack_health > self.rest_stop_health)[:, None]
        allowed = np.minimum(self.rest_count, headroom_left - self.spare_for_faults)
        return self._pick(-np.nan_to_num(L, nan=np.inf), eligible, allowed)

    def rest_hot(self, temp_measured, in_string, headroom_left) -> np.ndarray:
        """REON's BMS can bypass a 'hot' cell and let it rest (Tim Ren, hack Discord)."""
        if self.rest_temp_C <= 0:
            return np.zeros(in_string.shape, dtype=bool)
        w = in_string.astype(float)
        mean = (np.nan_to_num(temp_measured) * w).sum(axis=1, keepdims=True) / np.maximum(w.sum(axis=1, keepdims=True), 1)
        excess = temp_measured - mean
        return self._pick(excess, in_string & (excess > self.rest_temp_C), headroom_left - self.spare_for_faults)

    def rest(self, X, names, in_string, headroom_left) -> np.ndarray:
        """Cells to rest for this step only."""
        if self.rest_count <= 0:
            return np.zeros(in_string.shape, dtype=bool)
        score = self._column(X, names, self.rest_by)
        allowed = np.minimum(self.rest_count, headroom_left - self.spare_for_faults)
        return self._pick(score, in_string & (score > 0), allowed)


class RemainingLifeTracker:
    """Predicted remaining life of each cell, from MEASURED capacity only.

    Keeps the last ``months`` monthly capacity readings per cell. A cell's fade rate
    blends its own least-squares trend over that window (needs >= ``min_months``)
    with a fade-proportional pack prior, r_prior = r_pack (1 - Q_i) / mean(1 - Q),
    which steadies the noisy slope (fast pre-knee faders knee earlier: fitted
    correlation -0.47). Remaining life L_i = (Q_i - Q_retire) / r_i, in years.
    """

    def __init__(self, shape, steps_per_year: int = 12, months: int = 13, min_months: int = 6):
        self.buf = np.full(tuple(shape) + (months,), np.nan)
        self.t = (np.arange(months) - (months - 1)) / steps_per_year
        self.min_months = min_months

    def update(self, cap):
        self.buf[..., :-1] = self.buf[..., 1:]
        self.buf[..., -1] = cap

    def reset(self, mask):
        self.buf[mask] = np.nan

    def own_rate(self):
        v = np.isfinite(self.buf)
        n = v.sum(-1)
        y = np.where(v, self.buf, 0.0)
        t = np.where(v, self.t, 0.0)
        st, sy, stt, sty = t.sum(-1), y.sum(-1), (t * t).sum(-1), (t * y).sum(-1)
        den = n * stt - st * st
        with np.errstate(all="ignore"):
            slope = (n * sty - st * sy) / den
        return np.where((n >= self.min_months) & (den > 0), -slope, np.nan)   # fade per year

    def life(self, cap, active, retire_level):
        own = np.where(active, self.own_rate(), np.nan)
        fade = np.where(active & np.isfinite(cap), 1.0 - cap, np.nan)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)       # fewer than min_months of history yet
            r_pack = np.maximum(np.nanmean(own, axis=1, keepdims=True), 1e-4)
            mean_fade = np.maximum(np.nanmean(fade, axis=1, keepdims=True), 1e-4)
        prior = r_pack * np.maximum(fade, 1e-4) / mean_fade
        rate = np.maximum(np.where(np.isfinite(own), 0.5 * own + 0.5 * prior, prior), 1e-4)
        return np.where(active & np.isfinite(cap), (cap - retire_level) / rate, np.nan)


__all__ = ["ControlPolicy", "RemainingLifeTracker"]
