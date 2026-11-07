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

from dataclasses import dataclass, field

import numpy as np


@dataclass
class ControlPolicy:
    bypass_on_empty: bool = True
    bypass_on_fault: bool = True
    isolate_if: dict = field(default_factory=dict)
    rest_count: int = 0
    rest_by: str = "soh_gap"
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

    def rest(self, X, names, in_string, headroom_left) -> np.ndarray:
        """Cells to rest for this step only."""
        if self.rest_count <= 0:
            return np.zeros(in_string.shape, dtype=bool)
        score = self._column(X, names, self.rest_by)
        allowed = np.minimum(self.rest_count, headroom_left - self.spare_for_faults)
        return self._pick(score, in_string & (score > 0), allowed)


__all__ = ["ControlPolicy"]
