"""What REON's per-cell monitoring reports, with adjustable signals and noise.

The challenge brief lets us assume individual-cell monitoring of voltage,
temperature, SOC, SOH, capacity, resistance, open-circuit voltage and
performance history. Each of those is a ``SignalSpec`` here: switch it off, or
give it measurement noise, and everything downstream (the learned fault model,
the control policy) only sees what is measured. The simulator's physics (aging,
true fault hazard) always runs on the true cell state.

Electrical signals come from one representative discharge per time step:

* SOC at end of discharge: 1 - (charge the cell passed) / (its capacity).
* OCV: an open-circuit-voltage curve evaluated at that SOC (placeholder curve
  for a layered-oxide sodium-ion cell; replace with REON's).
* Voltage under load: OCV - I * R, at the pack's rated C-rate.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

SIGNALS = ("voltage", "temperature", "soc", "soh", "capacity", "resistance", "ocv", "history")


@dataclass
class SignalSpec:
    enabled: bool = True
    noise: float = 0.0        # sd of additive Gaussian noise, in the signal's unit (see MonitoringConfig)


def _spec(enabled=True, noise=0.0):
    return field(default_factory=lambda: SignalSpec(enabled, noise))


@dataclass
class MonitoringConfig:
    """Per-cell signals. Noise defaults are placeholders; ask REON for their sensor specs."""

    voltage: SignalSpec = _spec(True, 0.002)      # V, cell voltage under load at end of discharge
    temperature: SignalSpec = _spec(True, 0.5)    # degC
    soc: SignalSpec = _spec(True, 0.01)           # fraction, at end of discharge
    soh: SignalSpec = _spec(True, 0.01)           # fraction of the cell's own beginning-of-life capacity
    capacity: SignalSpec = _spec(True, 0.01)      # fraction of nameplate capacity
    resistance: SignalSpec = _spec(True, 0.02)    # relative (fraction of the reading)
    ocv: SignalSpec = _spec(True, 0.002)          # V, rest voltage after the discharge
    history: SignalSpec = _spec(True, 0.0)        # enables trend features (noise unused)
    history_months: int = 6                       # window for the fade-rate trend
    # electrical placeholders used to derive voltage / OCV
    c_rate: float = 0.5                           # EBS: 30 kW / 60 kWh
    r_nominal_mohm: float = 0.4                   # BOL cell resistance at 200 Ah
    ocv_v_min: float = 2.0
    ocv_v_max: float = 4.0

    @classmethod
    def perfect(cls) -> "MonitoringConfig":
        """Every signal on, no noise."""
        m = cls()
        for s in SIGNALS:
            getattr(m, s).noise = 0.0
        return m

    @classmethod
    def only(cls, *signals: str, noisy: bool = True) -> "MonitoringConfig":
        """Only the named signals enabled (e.g. a conventional BMS: voltage, temperature)."""
        unknown = set(signals) - set(SIGNALS)
        if unknown:
            raise ValueError(f"unknown signals {unknown}; choose from {SIGNALS}")
        m = cls() if noisy else cls.perfect()
        for s in SIGNALS:
            getattr(m, s).enabled = s in signals
        return m

    def enabled(self) -> list[str]:
        return [s for s in SIGNALS if getattr(self, s).enabled]

    def ocv_curve(self, soc):
        """Placeholder monotone OCV(SOC): sloped, with a mild S-shape."""
        s = np.clip(soc, 0.0, 1.0)
        shape = 0.8 * s + 0.2 * (0.5 + 0.5 * np.tanh(6.0 * (s - 0.5)) / np.tanh(3.0))
        return self.ocv_v_min + (self.ocv_v_max - self.ocv_v_min) * shape

    def feature_names(self) -> list[str]:
        """Model features available under this configuration, in a fixed order."""
        names = []
        if self.temperature.enabled:
            names.append("temp_offset_C")
        if self.soh.enabled or self.capacity.enabled:
            names.append("soh_gap")
        if self.resistance.enabled:
            names.append("resistance_gap")
        if self.voltage.enabled:
            names.append("eod_voltage_gap")
        if self.ocv.enabled:
            names.append("ocv_gap")
        if self.soc.enabled:
            names.append("soc_end")
        if self.history.enabled and (self.soh.enabled or self.capacity.enabled):
            names.append("fade_rate_gap")
        return names


class Monitor:
    """Turns the true cell state into noisy readings and pack-relative features."""

    def __init__(self, cfg: MonitoringConfig, steps_per_year: int, rng: np.random.Generator):
        self.cfg, self.rng = cfg, rng
        self.window = max(1, int(round(cfg.history_months * steps_per_year / 12)))
        self.dt_window = self.window / steps_per_year
        self._cap_hist: list[np.ndarray] = []
        self._fresh = None

    def _noisy(self, x, spec: SignalSpec, relative=False):
        if spec.noise <= 0:
            return x.copy()
        e = self.rng.standard_normal(x.shape) * spec.noise
        return x * (1.0 + e) if relative else x + e

    def read(self, Q, q0, R, temp, passed) -> dict:
        """Measured signals (NaN where disabled). ``passed`` = charge each cell gave
        in the last discharge, in nameplate units (0 for an idle cell)."""
        c = self.cfg
        out = {}
        nan = np.full(Q.shape, np.nan)
        soc_end = np.clip(1.0 - passed / np.maximum(Q, 1e-9), 0.0, 1.0)
        ocv = c.ocv_curve(soc_end)
        current = c.c_rate * 200.0                       # A, for a 200 Ah cell
        v_load = ocv - current * R * c.r_nominal_mohm / 1000.0
        out["temperature"] = self._noisy(temp, c.temperature) if c.temperature.enabled else nan
        out["soh"] = self._noisy(Q / q0, c.soh) if c.soh.enabled else nan
        out["capacity"] = self._noisy(Q, c.capacity) if c.capacity.enabled else nan
        out["resistance"] = self._noisy(R, c.resistance, relative=True) if c.resistance.enabled else nan
        out["soc"] = self._noisy(soc_end, c.soc) if c.soc.enabled else nan
        out["ocv"] = self._noisy(ocv, c.ocv) if c.ocv.enabled else nan
        out["voltage"] = self._noisy(v_load, c.voltage) if c.voltage.enabled else nan
        # history: measured capacity trend over the window
        cap = out["capacity"] if c.capacity.enabled else out["soh"]
        if self._fresh is not None:           # replaced cells start a new history
            for h in self._cap_hist:
                h[self._fresh] = cap[self._fresh]
            self._fresh = None
        self._cap_hist.append(cap)
        if len(self._cap_hist) > self.window + 1:
            self._cap_hist.pop(0)
        if c.history.enabled and len(self._cap_hist) > self.window:
            out["fade_rate"] = (self._cap_hist[0] - self._cap_hist[-1]) / self.dt_window
        else:
            out["fade_rate"] = np.zeros(Q.shape) if c.history.enabled else nan
        return out

    def reset_cells(self, mask):
        """A replaced cell has no history: its trend restarts at the next reading."""
        self._fresh = mask.copy() if self._fresh is None else (self._fresh | mask)

    def features(self, m: dict, active) -> np.ndarray:
        """Pack-relative features in ``cfg.feature_names()`` order, shape (P, N, F)."""
        c = self.cfg
        w = active.astype(float)
        n = np.maximum(w.sum(axis=1, keepdims=True), 1.0)

        def mean(x):
            return (np.nan_to_num(x) * w).sum(axis=1, keepdims=True) / n

        def median(x):
            return np.nanmedian(np.where(active, x, np.nan), axis=1, keepdims=True)

        cols = []
        if c.temperature.enabled:
            cols.append(m["temperature"] - mean(m["temperature"]))
        if c.soh.enabled or c.capacity.enabled:
            health = m["capacity"] if c.capacity.enabled else m["soh"]
            cols.append(mean(health) - health)
        if c.resistance.enabled:
            cols.append(m["resistance"] / median(m["resistance"]) - 1.0)
        if c.voltage.enabled:
            cols.append(median(m["voltage"]) - m["voltage"])
        if c.ocv.enabled:
            cols.append(median(m["ocv"]) - m["ocv"])
        if c.soc.enabled:
            cols.append(m["soc"])
        if c.history.enabled and (c.soh.enabled or c.capacity.enabled):
            cols.append(m["fade_rate"] - mean(m["fade_rate"]))
        if not cols:
            return np.zeros(active.shape + (0,))
        return np.nan_to_num(np.stack(cols, axis=-1))


__all__ = ["SIGNALS", "SignalSpec", "MonitoringConfig", "Monitor"]
