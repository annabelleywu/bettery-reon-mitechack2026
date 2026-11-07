"""Monte Carlo simulator: a fixed series string vs. per-cell bypass (REON).

Two effects, two kinds of math
------------------------------
1. Gradual drift (deterministic given cell parameters): every cell fades as
   sqrt(t) calendar aging + linear cycle aging, scaled by its own multiplier,
   then linearly faster after a cell-specific knee. The spread structure is
   calibrated on Zhou et al. (2026) per-cell data; see ``AgingConfig``.

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

Aging-spread defaults are calibrated (``scripts/calibrate.py``). The stationary
timeline (k_cal, k_cyc, knee transfer), the pack design and every fault-hazard
parameter remain assumptions for a sodium-ion C&I block (REON EBS: 30 kW / 60 kWh).
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass, field

import numpy as np

from .control import ControlPolicy, RemainingLifeTracker
from .monitoring import Monitor, MonitoringConfig

FEATURES = ["temp_offset_C", "soh_gap", "resistance_gap"]
R_GAS = 8.314
MIN_FRACTION = 0.05   # truncation for per-cell multipliers (fraction of the mean)
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
    retirement_retention: float = 0.70  # see retention_basis
    retention_basis: str = "nameplate"   # "nameplate", or "bol": this design's own beginning-of-life energy (brief's R_sys)
    rated_kw: float = 30.0               # inverter rating per block (REON EBS: 30 kW / 60 kWh)
    event_hours: float = 2.0             # firm kW must be held this long (committed event)
    v_floor: float = 2.5                 # per-cell discharge voltage floor for beta_power (placeholder)
    years: float = 15.0
    steps_per_year: int = 12

    @property
    def nameplate_kwh(self) -> float:
        return self.n_series * self.cell_ah * self.v_nominal / 1000.0


@dataclass
class AgingConfig:
    """Per-cell capacity fade, calibrated on Zhou et al. (2026) per-cell data.

        Q_i(a) = q0_i - m_i * B(a) - kappa_i * b_bar * (a - tau_i)_+

    * B(a) = k_cal*sqrt(a) + k_cyc*EFC(a): base fade of the mean cell (stationary
      duty: an ASSUMPTION, not from the EV data).
    * m_i: the cell's pre-knee fade multiplier (E[m] = 1).
    * tau_i = tau_bar * P_pack * tau_rel_i: knee onset. tau_bar (years) is a
      transfer ASSUMPTION; P_pack is the between-pack knee spread.
    * After the knee the cell fades linearly at kappa_i times the mean pre-knee
      rate b_bar = B(tau_bar)/tau_bar.
    * With ``throughput_aging`` the cycle term counts each cell's own
      equivalent full cycles (charge passed / nameplate charge), and the knee
      clock advances with the calendar share of aging plus the cycle share
      times the cell's use. A cell passing full nameplate charge every cycle
      reproduces the closed form above exactly; a bypassed or rested cell
      ages on calendar time only.
    * (m, tau_rel, kappa) are jointly normal across cells (see
      ``draw_cell_parameters``). Their covariance and the slope ratio come from
      hinge fits to 95 cells (``reon_model.calibration``); a slot's temperature
      offset carries the Arrhenius share of m.
    """

    # --- calibrated on Zhou et al. 2026 (data/calibration_zhou2026.json) ---
    q0_cv: float = 0.00473
    cell_cov: tuple = ((0.14341, -0.00787, 0.05951),
                       (-0.00787, 0.00194, -0.00919),
                       (0.05951, -0.00919, 0.12032))
    knee_slope_ratio: float = 8.3774     # mean post-knee slope / mean pre-knee slope
    knee_pack_logsd: float = 0.13853     # between-pack spread of knee onset
    kappa_spread_scale: float = 0.537    # post-knee slope spread shrink (1 = as fitted)
    knee_onset_fade: float = 0.07517     # mean-cell fade at knee onset (EV data transfer)
    r0_cv: float = 0.05918
    resistance_growth: float = 7.48153   # R/R0 = 1 + growth * fractional fade
    # --- chemistry-agnostic spread and paper-aligned outliers ---
    spread_multiplier: float = 1.0       # scales every within-pack spread (rate/knee/slope CVs, q0, r0); 1 = calibrated
    outlier_fraction: float = 0.0        # share of cells that knee early (Zhou et al.: less favourable initial
    outlier_knee_factor: float = 0.8     #   condition or harsher local history); their knee is multiplied by this
    # --- assumptions (not in the EV data) ---
    throughput_aging: bool = True        # cycle aging follows each cell's own charge throughput
    knee_onset_years: float | None = None  # None: solve B(tau_bar) = knee_onset_fade
    k_cal: float = 0.02                  # calendar fade per sqrt(year)   (assumption)
    k_cyc: float = 1.0e-5                # fade per equivalent full cycle (assumption)
    temp_sd_C: float = 2.0               # cell-to-cell temperature spread in the rack
    activation_energy: float = 50e3      # J/mol (Arrhenius)
    t_mean_C: float = 25.0

    def base_fade(self, age, cycles_per_year):
        age = np.asarray(age, dtype=float)
        return self.k_cal * np.sqrt(age) + self.k_cyc * cycles_per_year * age

    def knee_years(self, cycles_per_year) -> float:
        if self.knee_onset_years is not None:
            return float(self.knee_onset_years)
        from scipy.optimize import brentq
        return float(brentq(lambda a: self.base_fade(a, cycles_per_year) - self.knee_onset_fade, 1e-6, 1e3))

    @property
    def arrhenius_slope(self) -> float:
        """d ln(rate) / dT at the mean temperature (per degC)."""
        T = self.t_mean_C + 273.15
        return self.activation_energy / (R_GAS * T * T)

    @classmethod
    def from_calibration(cls, path, **overrides) -> "AgingConfig":
        import json
        c = json.loads(open(path).read())["aging"]
        c["cell_cov"] = tuple(tuple(r) for r in c["cell_cov"])
        c.update(overrides)
        return cls(**c)


def draw_cell_parameters(aging: AgingConfig, n: int, rng: np.random.Generator, temp=None) -> dict:
    """Draw n cells. If ``temp`` is given (slot temperatures), condition on it.

    (m, tau_rel, kappa/knee_slope_ratio) are multivariate normal with mean 1
    and covariance ``cell_cov`` (linear space: the fitted post-knee slopes are
    symmetric, so log-normal marginals would overstate the weak-cell tail),
    truncated below at ``MIN_FRACTION``. Temperature shifts m by the Arrhenius
    slope and moves tau and kappa only through their correlation with m.
    """
    s_mult = aging.spread_multiplier
    C3 = np.asarray(aging.cell_cov, dtype=float) * s_mult**2
    sT, a = aging.temp_sd_C, aging.arrhenius_slope
    mean3 = np.ones(3)
    if sT > 0:
        # temperature carries its Arrhenius share of the rate spread; capped (as in the web app) so a
        # narrow spread multiplier cannot make the conditional covariance negative
        rho = min(0.95, a * sT / np.sqrt(C3[0, 0])) if C3[0, 0] > 0 else 0.0
        c = rho * sT * C3[:, 0] / np.sqrt(C3[0, 0]) if C3[0, 0] > 0 else np.zeros(3)
        if temp is None:
            temp = sT * rng.standard_normal(n)
        cond_mean = mean3 + np.outer(temp, c) / sT**2
        z = cond_mean + rng.multivariate_normal(np.zeros(3), C3 - np.outer(c, c) / sT**2, n)
    else:
        temp = np.zeros(n)
        z = rng.multivariate_normal(mean3, C3, n)
    z[:, 2] = 1.0 + aging.kappa_spread_scale * (z[:, 2] - 1.0)
    z = np.maximum(z, MIN_FRACTION)
    if aging.outlier_fraction > 0:          # draw only when used, so the default RNG stream is unchanged
        z[:, 1] = np.where(rng.random(n) < aging.outlier_fraction, z[:, 1] * aging.outlier_knee_factor, z[:, 1])
    return {
        "temp": np.asarray(temp, dtype=float),
        "m": z[:, 0], "tau_rel": z[:, 1], "kappa": aging.knee_slope_ratio * z[:, 2],
        "q0": 1.0 + aging.q0_cv * s_mult * rng.standard_normal(n),
        "r0": 1.0 + aging.r0_cv * s_mult * rng.standard_normal(n),
    }


@dataclass
class HazardConfig:
    """Fault-hazard NHPP parameters. PLACEHOLDERS: the paper data has no fault events."""

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
    def off(cls) -> "HazardConfig":
        """No sudden faults. The paper's data has no fault events and describes gradual drift into a
        knee, so value comparisons use this; the fault model stays available as a sensitivity."""
        return cls(base_rate=0.0)

    @classmethod
    def homogeneous(cls, rate: float) -> "HazardConfig":
        """All cells share one constant rate: the simple Poisson special case."""
        return cls(base_rate=rate, coef={f: 0.0 for f in FEATURES})


def discharge(Q, active, headroom):
    """One full discharge. Returns (string charge, charge each cell passed).

    Series cells share one current. Sorted active capacities Q_(1) <= ...; with
    h cells allowed to drop out, the string stops when the (h+1)-th weakest
    empties, and cell i passes min(Q_i, Q_(h+1)). h = 0: every cell passes
    min Q (fixed string). Q, active: (P, N); headroom: (P,) int >= 0.
    """
    Q = np.asarray(Q, dtype=float)
    Qs = np.sort(np.where(active, Q, np.inf), axis=1)
    n_active = active.sum(axis=1)
    h = np.clip(np.asarray(headroom), 0, np.maximum(n_active - 1, 0))
    stop = np.take_along_axis(Qs, h[:, None], axis=1)
    passed = np.where(active, np.minimum(Q, stop), 0.0)
    passed = np.where((n_active > 0)[:, None], passed, 0.0)
    return passed.sum(axis=1), passed


def usable_capacity(Q, active, headroom):
    """sum_i min(Q_i, Q_(h+1)) over active cells (see ``discharge``)."""
    return discharge(Q, active, headroom)[0]


def beta_power(R, active, headroom, ocv_mid, v_floor):
    """Power utilisation (Zhou et al. 2026, eq. 12, simplified), shape (P,).

    Cells at a reference SOC with open-circuit voltage ``ocv_mid`` may each draw
    I_i = (ocv_mid - v_floor) / R_i before hitting the voltage floor. Series cells
    share one current, so a fixed string runs at min_i I_i and delivers
    sum_j I (ocv_mid - R_j I). With bypass, up to ``headroom`` of the
    highest-resistance active cells may be switched out first; the best case is
    kept. The denominator is the sum of cell peak powers I_i * v_floor over the
    active cells. The absolute resistance scale cancels.
    """
    R = np.asarray(R, dtype=float)
    dv = ocv_mid - v_floor
    Rs = np.sort(np.where(active, R, -np.inf), axis=1)[:, ::-1]      # active, highest resistance first
    n_act = active.sum(axis=1)
    denom = np.where(active, dv / np.where(active, R, 1.0) * v_floor, 0.0).sum(axis=1)
    h_max = int(np.max(np.minimum(headroom, np.maximum(n_act - 1, 0)))) if len(n_act) else 0
    best = np.zeros(R.shape[0])
    valid = np.isfinite(Rs)
    for d in range(h_max + 1):
        Rd = Rs[:, d]
        ok = (d <= np.minimum(headroom, n_act - 1)) & np.isfinite(Rd) & (Rd > 0)
        I = np.where(ok, dv / np.where(ok, Rd, 1.0), 0.0)
        keep = valid & (np.arange(R.shape[1])[None, :] >= d)
        p = (I[:, None] * (ocv_mid - np.where(keep, Rs, 0.0) * I[:, None]) * keep).sum(axis=1)
        best = np.where(ok, np.maximum(best, p), best)
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(denom > 0, best / denom, np.nan)


class _CellSlots:
    """State of P packs x N cell slots (a slot gets a new cell when replaced)."""

    def __init__(self, P, N, aging: AgingConfig, cycles_per_year: float, rng: np.random.Generator):
        self.aging, self.rng, self.cpy = aging, rng, cycles_per_year
        self.P, self.N = P, N
        self.tau_bar = aging.knee_years(cycles_per_year)
        self.b_bar = float(aging.base_fade(self.tau_bar, cycles_per_year)) / self.tau_bar
        s = aging.knee_pack_logsd
        self.pack_knee = rng.lognormal(-s * s / 2, s, (P, 1)) if s > 0 else np.ones((P, 1))
        B = float(aging.base_fade(self.tau_bar, cycles_per_year))
        self.w_cal = aging.k_cal * np.sqrt(self.tau_bar) / B     # calendar share of aging
        self.w_cyc = 1.0 - self.w_cal                             # cycle share at full use
        shape = (P, N)
        for name in ("q0", "r0", "temp", "m", "tau", "kappa", "installed", "budget", "cum", "efc", "clock"):
            setattr(self, name, np.zeros(shape))
        self._fill(np.ones(shape, dtype=bool), t=0.0, initial=True)

    def _fill(self, mask, t, initial=False):
        n = int(mask.sum())
        if n == 0:
            return
        # rack temperature belongs to the slot: a replacement cell inherits it
        d = draw_cell_parameters(self.aging, n, self.rng, temp=None if initial else self.temp[mask])
        for name in ("q0", "r0", "m", "kappa", "temp"):
            getattr(self, name)[mask] = d[name]
        self.tau[mask] = self.tau_bar * np.broadcast_to(self.pack_knee, mask.shape)[mask] * d["tau_rel"]
        self.installed[mask] = t
        self.budget[mask] = self.rng.exponential(1.0, n)
        self.cum[mask] = 0.0
        self.efc[mask] = 0.0
        self.clock[mask] = 0.0

    def replace(self, mask, t):
        self._fill(mask, t)

    def advance(self, dt, use):
        """Age every cell by dt years. ``use`` = charge passed per cycle in
        nameplate units (1 = a full nameplate cycle), shape (P, N)."""
        if not self.aging.throughput_aging:
            use = np.ones_like(self.efc)
        use = np.clip(use, 0.0, None)
        self.efc += use * self.cpy * dt
        self.clock += dt * (self.w_cal + self.w_cyc * use)

    def capacity(self, t):
        age = np.maximum(t - self.installed, 0.0)
        fade = self.m * (self.aging.k_cal * np.sqrt(age) + self.aging.k_cyc * self.efc)
        fade += self.kappa * self.b_bar * np.maximum(self.clock - self.tau, 0.0)
        return np.clip(self.q0 - fade, 0.0, None)

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
    isolated: np.ndarray | None = None   # (P,) cells proactively isolated over horizon
    rested_cell_steps: np.ndarray | None = None  # (P,) cell-steps spent resting
    rows: dict | None = None      # cell-period training rows on MEASURED features (if recorded)
    firm_kw: np.ndarray | None = None     # (P, K) min(rated kW, usable kWh / event hours) x availability; 0 after retirement
    beta_power: np.ndarray | None = None  # (P, K) power utilisation (see ``beta_power``)
    beta_soh: np.ndarray | None = None    # (P, K) min / mean capacity of discharging cells


def simulate(mode: str, n_packs: int = 200, pack: PackConfig = PackConfig(),
             aging: AgingConfig = AgingConfig(), hazard: HazardConfig = HazardConfig(),
             seed: int = 0, record_rows: bool = False,
             monitoring: MonitoringConfig | None = None, policy: ControlPolicy | None = None) -> SimResult:
    """mode = 'fixed' (conventional string) or 'bypass' (cell-level control under ``policy``).

    ``monitoring`` sets which signals the controller and the learned model see
    (default: all signals, placeholder noise). The fault hazard and aging always
    use the true cell state. ``policy`` defaults to ``ControlPolicy()`` (bypass
    on empty and on fault, nothing proactive); it is ignored in 'fixed' mode.
    """
    if mode not in ("fixed", "bypass"):
        raise ValueError(mode)
    policy = ControlPolicy.conventional() if mode == "fixed" else (policy or ControlPolicy())
    monitoring = monitoring or MonitoringConfig()
    rng = np.random.default_rng(seed)       # same seed -> same initial cells in both modes
    P, N = n_packs, pack.n_series
    dt = 1.0 / pack.steps_per_year
    K = int(round(pack.years * pack.steps_per_year))
    t_grid = np.arange(K) * dt
    slots = _CellSlots(P, N, aging, pack.cycles_per_year, rng)
    monitor = Monitor(monitoring, pack.steps_per_year, np.random.default_rng(seed + 10_007))
    tracker = (RemainingLifeTracker((P, N), pack.steps_per_year)
               if (mode == "bypass" and policy.rest_count > 0 and policy.rest_by == "remaining_life") else None)
    names = monitoring.feature_names()
    beta = hazard.beta
    k_max = pack.bypass_headroom if mode == "bypass" else 0

    bypassed = np.zeros((P, N), dtype=bool)  # out of the string until the next service
    passed = np.zeros((P, N))                # charge each cell gave in the last discharge
    downtime_left = np.zeros(P)              # days of outage still to serve
    energy = np.zeros((P, K)); avail = np.ones((P, K))
    bpow = np.zeros((P, K)); bsoh = np.zeros((P, K))
    ocv_mid = float(monitoring.ocv_curve(0.5))
    faults = np.zeros(P); visits = np.zeros(P); isolated = np.zeros(P); rested_steps = np.zeros(P)
    rows = {"X": [], "events": [], "exposure": [], "pack": [], "t": []} if record_rows else None
    days_per_step = 365.0 * dt

    for k, t in enumerate(t_grid):
        Q = slots.capacity(t)
        R = slots.resistance(Q)
        in_string = ~bypassed
        # --- what the BMS measures, and the controller's choices -------------
        meas = monitor.read(Q, slots.q0, R, slots.temp, passed)
        Xm = monitor.features(meas, in_string)
        cap_meas = meas["capacity"] if monitoring.capacity.enabled else meas["soh"]
        if tracker is not None:
            tracker.update(cap_meas)
        left = k_max - bypassed.sum(axis=1)
        iso = policy.isolate(Xm, names, in_string, left)
        bypassed |= iso
        isolated += iso.sum(axis=1)
        in_string = ~bypassed
        left = k_max - bypassed.sum(axis=1)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)       # no capacity signal measured
            pack_health = np.nanmean(np.where(in_string, cap_meas, np.nan), axis=1)
        pack_health = np.nan_to_num(pack_health, nan=1.0)
        if policy.rest_by == "remaining_life":
            if tracker is not None and np.isfinite(cap_meas).any():
                life = tracker.life(cap_meas, in_string, pack.retirement_retention)
                rested = policy.rest_by_life(life, in_string, left, pack_health)
            else:
                rested = np.zeros((P, N), dtype=bool)
        else:
            rested = policy.rest(Xm, names, in_string, left) & (pack_health > policy.rest_stop_health)[:, None]
        if policy.rest_temp_C > 0 and monitoring.temperature.enabled:
            rested |= policy.rest_hot(meas["temperature"], in_string & ~rested, left - rested.sum(axis=1))
        rested_steps += rested.sum(axis=1)
        discharging = in_string & ~rested
        headroom = (left - rested.sum(axis=1)) if policy.bypass_on_empty else np.zeros(P, dtype=int)

        # --- true fault hazard (cells out of the string are not at risk) -------
        X = cell_features(Q, R, slots.temp, in_string)
        lam = hazard.base_rate * np.exp(X @ beta) * in_string

        # --- usable energy at the start of this step ---------------------------
        cap, passed = discharge(Q, discharging, headroom)
        if mode == "bypass":
            cap = cap * pack.switch_efficiency
        energy[:, k] = cap * pack.cell_ah * pack.v_nominal / 1000.0
        bpow[:, k] = beta_power(R, discharging, headroom, ocv_mid, pack.v_floor)
        Qd = np.where(discharging, Q, np.nan)
        with np.errstate(invalid="ignore", divide="ignore"):
            bsoh[:, k] = np.nanmin(Qd, axis=1) / np.nanmean(Qd, axis=1)

        # --- faults within this step (exact for piecewise-constant hazard) -------
        cum_prev = slots.cum.copy()
        slots.cum += lam * dt
        fault = in_string & (slots.cum >= slots.budget)
        if record_rows:
            with np.errstate(divide="ignore", invalid="ignore"):
                expo = np.where(fault, (slots.budget - cum_prev) / lam, dt)
            m = in_string
            rows["X"].append(Xm[m]); rows["events"].append(fault[m].astype(float))
            rows["exposure"].append(expo[m]); rows["pack"].append(np.nonzero(m)[0])
            rows["t"].append(np.full(int(m.sum()), t))
        n_fault = fault.sum(axis=1)
        faults += n_fault

        # --- control response ------------------------------------------------
        if not policy.bypass_on_fault:
            # any fault stops the string; a technician swaps the cell
            visits += n_fault
            downtime_left += n_fault * pack.repair_days
            swap = fault
        else:
            bypassed |= fault
            over = bypassed.sum(axis=1) > k_max
            visits += over
            downtime_left += over * pack.repair_days
            swap = bypassed & over[:, None]
            bypassed &= ~swap

        served = np.minimum(downtime_left, days_per_step)
        avail[:, k] = 1.0 - served / days_per_step
        downtime_left -= served
        slots.advance(dt, passed * avail[:, k][:, None])
        slots.replace(swap, t + dt)
        monitor.reset_cells(swap)
        if tracker is not None:
            tracker.reset(swap)
        passed = np.where(swap, 0.0, passed)

    if pack.retention_basis == "bol":
        retention = energy / np.maximum(energy[:, :1], 1e-12)     # brief's R_sys: vs this design's own start
    elif pack.retention_basis == "nameplate":
        retention = energy / pack.nameplate_kwh
    else:
        raise ValueError(pack.retention_basis)
    below = retention < pack.retirement_retention
    first = np.where(below.any(axis=1), below.argmax(axis=1), K)
    retire = np.where(first < K, t_grid[np.minimum(first, K - 1)], np.inf)
    in_life = np.arange(K)[None, :] < first[:, None]
    delivered = (energy * avail * in_life).sum(axis=1) * pack.cycles_per_year * dt / 1000.0

    if record_rows:
        rows = {key: np.concatenate(v) for key, v in rows.items()}
        rows["feature_names"] = names
    firm_kw = np.minimum(pack.rated_kw, energy / pack.event_hours) * avail * in_life
    return SimResult(mode, t_grid, energy, retention, avail, faults, visits, retire, delivered,
                     isolated, rested_steps, rows, firm_kw, bpow, bsoh)


def compare(n_packs=200, pack=PackConfig(), aging=AgingConfig(), hazard=HazardConfig(), seed=0,
            monitoring=None, policy=None):
    """Run both architectures on identical initial cells (common random numbers)."""
    return {m: simulate(m, n_packs, pack, aging, hazard, seed, monitoring=monitoring, policy=policy)
            for m in ("fixed", "bypass")}


__all__ = ["FEATURES", "PackConfig", "AgingConfig", "draw_cell_parameters", "HazardConfig", "SimResult", "beta_power",
           "simulate", "compare", "discharge", "usable_capacity", "cell_features"]
