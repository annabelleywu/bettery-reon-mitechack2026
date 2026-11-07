"""Monte Carlo simulator: a fixed series string vs. per-cell bypass (REON).

Two effects, two kinds of math
------------------------------
1. Gradual drift (deterministic given cell parameters): every cell fades as
   sqrt(t) calendar aging + linear cycle aging, scaled by its own aging
   multiplier (manufacturing spread x Arrhenius temperature factor), plus a
   "knee" of accelerated fade after a cell-specific onset time.

2. Sudden faults (stochastic): each cell's hard-fault process is an NHPP with
   intensity lambda_i(t) = lambda_0 * exp(beta . x_i(t)), where x_i(t) are
   telemetry features (see ``FEATURES``). The intensity is held constant
   within each time step, so fault times are drawn *exactly* by time
   rescaling: a cell faults when its accumulated hazard passes an Exp(1)
   budget. With beta = 0 this is a homogeneous Poisson process with rate
   lambda_0 per cell (N*lambda_0 for the pack).

Usable energy per discharge
---------------------------
Series cells share one current. Sort active capacities Q_(1) <= ... <= Q_(n).
If the inverter's voltage window lets h more cells drop out mid-discharge,
the string stops when the (h+1)-th weakest cell empties, so the delivered
charge is

    sum_i min(Q_i, Q_(h+1)).

h = 0 is the fixed string (n * min Q). h = n-1 is "every cell runs to its own
end" (sum Q). See ``usable_capacity``.

All parameter defaults are placeholders chosen to be plausible for a
stationary sodium-ion C&I block (REON EBS: 30 kW / 60 kWh). Replace them with
calibrated values (Zhou et al. 2026 fleet data, TUM Na-ion data, REON input).
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

FEATURES = ["temp_offset_C", "soh_gap", "resistance_gap"]
R_GAS = 8.314
T_REF_K = 298.15


@dataclass
class PackConfig:
    n_series: int = 96               # cells in series
    cell_ah: float = 200.0           # nameplate Ah per cell
    v_nominal: float = 3.1           # V per cell (Na-ion layered oxide)
    bypass_headroom: int = 4         # k: cells the voltage window lets you drop
    switch_efficiency: float = 0.995 # conduction loss of per-cell switches
    repair_days: float = 14.0        # outage per service visit
    cycles_per_year: float = 365.0
    retirement_retention: float = 0.70  # vs nameplate energy
    years: float = 15.0
    steps_per_year: int = 12

    @property
    def nameplate_kwh(self) -> float:
        return self.n_series * self.cell_ah * self.v_nominal / 1000.0


@dataclass
class AgingConfig:
    q0_cv: float = 0.01              # BOL capacity spread (new cells)
    multiplier_sigma: float = 0.15   # lognormal sd of per-cell aging rate
    k_cal: float = 0.02              # calendar fade per sqrt(year)
    k_cyc: float = 1.0e-5            # fade per equivalent full cycle
    temp_sd_C: float = 2.0           # cell-to-cell temperature spread in the rack
    activation_energy: float = 50e3  # J/mol (Arrhenius)
    t_mean_C: float = 25.0
    knee_shape: float = 6.0          # Weibull shape for knee onset
    knee_scale_years: float = 20.0   # Weibull scale, divided by the aging multiplier
    knee_rate: float = 0.03          # extra fade per year^2 after the knee
    r0_cv: float = 0.03              # BOL resistance spread
    resistance_growth: float = 3.0   # R/R0 = 1 + growth * fractional fade


@dataclass
class HazardConfig:
    base_rate: float = 0.0015        # hard faults per cell-year at x = 0
    coef: dict = field(default_factory=lambda: {
        "temp_offset_C": 0.12,       # per degC hotter than pack mean
        "soh_gap": 10.0,             # per unit of SOH below pack mean
        "resistance_gap": 1.5,       # per unit of relative resistance above median
    })

    @property
    def beta(self) -> np.ndarray:
        return np.array([self.coef[f] for f in FEATURES])

    @classmethod
    def homogeneous(cls, rate: float) -> "HazardConfig":
        """All cells share one constant rate: the simple Poisson special case."""
        return cls(base_rate=rate, coef={f: 0.0 for f in FEATURES})


def usable_capacity(Q, active, headroom):
    """sum_i min(Q_i, Q_(h+1)) over active cells, vectorized over packs.

    Q, active: (P, N); headroom: (P,) int >= 0. Returns (P,) in Q units.
    """
    Q = np.asarray(Q, dtype=float)
    Qs = np.sort(np.where(active, Q, np.inf), axis=1)
    n_active = active.sum(axis=1)
    h = np.clip(np.asarray(headroom), 0, np.maximum(n_active - 1, 0))
    stop = np.take_along_axis(Qs, h[:, None], axis=1)
    contrib = np.where(active, np.minimum(Q, stop), 0.0)
    return np.where(n_active > 0, contrib.sum(axis=1), 0.0)


class _CellSlots:
    """State of P packs x N cell slots (a slot gets a new cell when replaced)."""

    def __init__(self, P, N, aging: AgingConfig, rng: np.random.Generator):
        self.aging, self.rng = aging, rng
        self.P, self.N = P, N
        shape = (P, N)
        self.q0 = np.empty(shape); self.r0 = np.empty(shape)
        self.temp = np.empty(shape); self.mult = np.empty(shape)
        self.knee = np.empty(shape); self.installed = np.zeros(shape)
        self.budget = np.empty(shape); self.cum = np.zeros(shape)
        self._fill(np.ones(shape, dtype=bool), t=0.0)

    def _fill(self, mask, t):
        a, rng, n = self.aging, self.rng, int(mask.sum())
        if n == 0:
            return
        self.q0[mask] = 1.0 + a.q0_cv * rng.standard_normal(n)
        self.r0[mask] = 1.0 + a.r0_cv * rng.standard_normal(n)
        # rack temperature is a property of the slot, not the cell: keep it on replacement
        if t == 0.0:
            self.temp[mask] = a.temp_sd_C * rng.standard_normal(n)
        T = a.t_mean_C + self.temp[mask] + 273.15
        arrhenius = np.exp(a.activation_energy / R_GAS * (1.0 / T_REF_K - 1.0 / T))
        self.mult[mask] = rng.lognormal(0.0, a.multiplier_sigma, n) * arrhenius
        self.knee[mask] = a.knee_scale_years * rng.weibull(a.knee_shape, n) / self.mult[mask]
        self.installed[mask] = t
        self.budget[mask] = rng.exponential(1.0, n)
        self.cum[mask] = 0.0

    def replace(self, mask, t):
        self._fill(mask, t)

    def capacity(self, t, cycles_per_year):
        a = self.aging
        age = np.maximum(t - self.installed, 0.0)
        fade = self.mult * (a.k_cal * np.sqrt(age) + a.k_cyc * cycles_per_year * age)
        fade += self.mult * a.knee_rate * np.maximum(age - self.knee, 0.0) ** 2
        return np.clip(self.q0 * (1.0 - fade), 0.0, None)

    def resistance(self, Q):
        frac_fade = np.clip(1.0 - Q / self.q0, 0.0, 1.0)
        return self.r0 * (1.0 + self.aging.resistance_growth * frac_fade)


def cell_features(Q, R, temp, active):
    """Telemetry features per cell, relative to the active cells of its pack."""
    w = active.astype(float)
    n = np.maximum(w.sum(axis=1, keepdims=True), 1.0)
    soh_mean = (Q * w).sum(axis=1, keepdims=True) / n
    R_med = np.nanmedian(np.where(active, R, np.nan), axis=1, keepdims=True)
    temp_mean = (temp * w).sum(axis=1, keepdims=True) / n
    return np.stack([temp - temp_mean, soh_mean - Q, R / R_med - 1.0], axis=-1)


@dataclass
class SimResult:
    mode: str
    t: np.ndarray                 # (K,) years at start of each step
    energy_kwh: np.ndarray        # (P, K) usable energy per full discharge
    retention: np.ndarray         # (P, K) energy / nameplate
    availability: np.ndarray      # (P, K) fraction of step in service
    faults: np.ndarray            # (P,) hard faults over horizon
    service_visits: np.ndarray    # (P,) outages
    retirement_year: np.ndarray   # (P,) first t with retention < threshold (inf if none)
    delivered_mwh: np.ndarray     # (P,) energy delivered until retirement/horizon
    rows: dict | None = None      # cell-period training rows (if recorded)


def simulate(mode: str, n_packs: int = 200, pack: PackConfig = PackConfig(),
             aging: AgingConfig = AgingConfig(), hazard: HazardConfig = HazardConfig(),
             seed: int = 0, record_rows: bool = False) -> SimResult:
    """mode = 'fixed' (conventional string) or 'bypass' (cell-level control)."""
    if mode not in ("fixed", "bypass"):
        raise ValueError(mode)
    rng = np.random.default_rng(seed)       # same seed -> same initial cells in both modes
    P, N = n_packs, pack.n_series
    dt = 1.0 / pack.steps_per_year
    K = int(round(pack.years * pack.steps_per_year))
    t_grid = np.arange(K) * dt
    slots = _CellSlots(P, N, aging, rng)
    beta = hazard.beta

    bypassed = np.zeros((P, N), dtype=bool)
    downtime_left = np.zeros(P)              # days of outage still to serve
    energy = np.zeros((P, K)); avail = np.ones((P, K))
    faults = np.zeros(P); visits = np.zeros(P)
    rows = {"X": [], "events": [], "exposure": [], "pack": [], "t": []} if record_rows else None
    days_per_step = 365.0 * dt

    for k, t in enumerate(t_grid):
        active = ~bypassed
        Q = slots.capacity(t, pack.cycles_per_year)
        R = slots.resistance(Q)
        X = cell_features(Q, R, slots.temp, active)
        lam = hazard.base_rate * np.exp(X @ beta) * active  # bypassed cells are not at risk

        # --- usable energy at the start of this step ---------------------------
        if mode == "fixed":
            cap = N * Q.min(axis=1)
        else:
            headroom = pack.bypass_headroom - bypassed.sum(axis=1)
            cap = usable_capacity(Q, active, headroom) * pack.switch_efficiency
        energy[:, k] = cap * pack.cell_ah * pack.v_nominal / 1000.0

        # --- faults within this step (exact for piecewise-constant hazard) -------
        cum_prev = slots.cum.copy()
        slots.cum += lam * dt
        fault = active & (slots.cum >= slots.budget)
        if record_rows:
            with np.errstate(divide="ignore", invalid="ignore"):
                expo = np.where(fault, (slots.budget - cum_prev) / lam, dt)
            m = active
            rows["X"].append(X[m]); rows["events"].append(fault[m].astype(float))
            rows["exposure"].append(expo[m]); rows["pack"].append(np.nonzero(m)[0])
            rows["t"].append(np.full(int(m.sum()), t))
        n_fault = fault.sum(axis=1)
        faults += n_fault

        # --- control response ------------------------------------------------
        if mode == "fixed":
            # any fault stops the string; a technician swaps the cell
            visits += n_fault
            downtime_left += n_fault * pack.repair_days
            slots.replace(fault, t + dt)
        else:
            bypassed |= fault
            over = bypassed.sum(axis=1) > pack.bypass_headroom
            visits += over
            downtime_left += over * pack.repair_days
            swap = bypassed & over[:, None]
            slots.replace(swap, t + dt)
            bypassed &= ~swap

        served = np.minimum(downtime_left, days_per_step)
        avail[:, k] = 1.0 - served / days_per_step
        downtime_left -= served

    retention = energy / pack.nameplate_kwh
    below = retention < pack.retirement_retention
    first = np.where(below.any(axis=1), below.argmax(axis=1), K)
    retire = np.where(first < K, t_grid[np.minimum(first, K - 1)], np.inf)
    in_life = np.arange(K)[None, :] < first[:, None]
    delivered = (energy * avail * in_life).sum(axis=1) * pack.cycles_per_year * dt / 1000.0

    if record_rows:
        rows = {key: np.concatenate(v) for key, v in rows.items()}
    return SimResult(mode, t_grid, energy, retention, avail, faults, visits, retire, delivered, rows)


def compare(n_packs=200, pack=PackConfig(), aging=AgingConfig(), hazard=HazardConfig(), seed=0):
    """Run both architectures on identical initial cells (common random numbers)."""
    return {m: simulate(m, n_packs, pack, aging, hazard, seed) for m in ("fixed", "bypass")}


__all__ = ["FEATURES", "PackConfig", "AgingConfig", "HazardConfig", "SimResult",
           "simulate", "compare", "usable_capacity", "cell_features"]
