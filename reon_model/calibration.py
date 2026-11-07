"""Calibrate the cell-aging model on Zhou et al. (2026), Nature Energy.

Source: github.com/Rico-dicp/Ev-battery-cell-to-cell-inconsistency (MIT licence),
folder "Source Data of Figures in Manuscript". Fetch it with
``scripts/fetch_paper_data.sh``. Data are NMC passenger-car cells (95 in series),
with capacities estimated from field signals (not lab-measured).

What is fitted, from which figure
---------------------------------
Fig. 3g/3h  per-cell capacity and resistance trajectories for one car, 74k-303k km.
    Each cell gets a hinge fit  Q = a - e*(x - x0) - s*(x - tau)_+.
    -> covariance of (m, tau_rel, kappa_rel) = (e, tau, s) / their means; slope ratio
       mean(s)/mean(e); BOL spread sd(a)/mean(a); resistance growth and spread.
Fig. 4      capacity of 95 cells in each of 12 cars at 80k and 280k km.
    -> each car's knee onset from its mean fade -> between-pack spread of knee
       onset (log-normal, right-censored for cars without a knee yet).
Fig. 5      sigma_SOH, beta_SOH vs mileage and beta_life for 19 cars.
    -> NOT used in fitting; held out to validate the calibrated model.

What does NOT come from this data
---------------------------------
* The stationary timeline (k_cal, k_cyc) and when the knee happens in years.
  ``knee_onset_fade`` transfers the knee by matching the mean cell's fade at
  onset; treat it as a scenario and run sensitivity on it.
* Any fault-hazard parameter: the repo contains no fault events.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import optimize, stats

from .simulate import AgingConfig, draw_cell_parameters

SRC_SUBDIR = "Source Data of Figures in Manuscript"
EOL_SOH = 0.85            # paper's beta_life threshold (07_indicator_calculation.py)


# --------------------------------------------------------------------- loading
def _src(path) -> Path:
    p = Path(path)
    return p / SRC_SUBDIR if (p / SRC_SUBDIR).is_dir() else p


def load_trajectories(path, cache: bool = True):
    """km (T,), Q (T, 95), R (T, 95) for the Fig. 3g/3h car. Cached as .npz."""
    src = _src(path)
    cache_file = src.parent / "fig3_trajectories.npz"
    if cache and cache_file.exists():
        z = np.load(cache_file)
        return z["km"], z["Q"], z["R"]
    g = pd.read_excel(src / "Source Data Fig. 3 a-g.xlsx", sheet_name="Fig3g")
    h = pd.read_excel(src / "Source Data Fig. 3 h-j.xlsx", sheet_name="Fig3h")
    g.columns, h.columns = ["km", "v", "cell"], ["km", "v", "cell"]
    Q = g.pivot_table(index="km", columns="cell", values="v")
    R = h.pivot_table(index="km", columns="cell", values="v").reindex(Q.index)
    km, Q, R = Q.index.to_numpy(float), Q.to_numpy(float), R.to_numpy(float)
    if cache:
        np.savez_compressed(cache_file, km=km, Q=Q, R=R)
    return km, Q, R


def load_fig4(path):
    """List of (Q at 80k km, Q at 280k km) per car (12 cars x 95 cells)."""
    x = pd.ExcelFile(_src(path) / "Source Data Fig. 4.xlsx")
    out = []
    for s in x.sheet_names:
        df = x.parse(s)
        out.append((df.iloc[:, 1].to_numpy(float), df.iloc[:, 2].to_numpy(float)))
    return out


def load_fig5(path) -> dict:
    x = pd.ExcelFile(_src(path) / "Source Data Fig. 5.xlsx")
    a = x.parse("Fig5a"); a.columns = ["vehicle", "km", "sigma_soh"]
    b = x.parse("Fig5b"); b.columns = ["vehicle", "km", "beta_soh"]
    c = x.parse("Fig5c"); c.columns = ["vehicle", "beta_life"]
    return {"sigma_soh": a, "beta_soh": b, "beta_life": c}


# --------------------------------------------------------------------- fitting
def fit_hinges(km, Q, tau_grid=None) -> pd.DataFrame:
    """Per-cell  Q = a - e*(x - x0) - s*(x - tau)_+  by grid search on tau.

    The design matrix depends only on tau, so all cells are solved at once.
    """
    km = np.asarray(km, float)
    x0 = km[0]
    tau_grid = np.arange(km[0] + 50, km[-1] - 5, 0.5) if tau_grid is None else tau_grid
    best_sse = np.full(Q.shape[1], np.inf)
    best = np.zeros((Q.shape[1], 4))
    for tau in tau_grid:
        A = np.column_stack([np.ones_like(km), -(km - x0), -np.maximum(km - tau, 0.0)])
        coef, *_ = np.linalg.lstsq(A, Q, rcond=None)
        sse = ((A @ coef - Q) ** 2).sum(axis=0)
        better = sse < best_sse
        best_sse[better] = sse[better]
        best[better, :3] = coef[:, better].T
        best[better, 3] = tau
    df = pd.DataFrame(best, columns=["a", "e", "s", "tau"])
    df["rmse"] = np.sqrt(best_sse / len(km))
    df["x0"] = x0
    return df


def fit_cell_structure(h: pd.DataFrame) -> dict:
    e_mean = h.e.mean()
    rel = np.column_stack([h.e / e_mean, h.tau / h.tau.mean(), h.s / h.s.mean()])
    return {
        "cell_cov": np.cov(rel, rowvar=False).round(5).tolist(),
        "skew_e_tau_s": [float(stats.skew(c)) for c in rel.T],
        "knee_slope_ratio": float(h.s.mean() / e_mean),
        "q0_cv": float(h.a.std() / h.a.mean()),
        "e_mean_per_1000km": float(e_mean),
        "s_mean_per_1000km": float(h.s.mean()),
        "tau_mean_km": float(h.tau.mean()),
        "a_mean": float(h.a.mean()),
        "x0_km": float(h.x0.iloc[0]),
        "hinge_rmse_median": float(h.rmse.median()),
    }


def fit_resistance(Q, R) -> dict:
    """R/R0 - 1 against fractional fade since the first observation, per cell."""
    frac_fade = 1.0 - Q[-1] / Q[0]
    growth = R[-1] / R[0] - 1.0
    return {"r0_cv": float(R[0].std() / R[0].mean()),
            "resistance_growth": float(growth.mean() / frac_fade.mean()),
            "corr_capacity_resistance_end": float(stats.pearsonr(Q[-1], R[-1])[0])}


def fit_pack_knee_spread(fig4, e_mean, s_mean, x1=80.0, x2=280.0, min_post_knee_km=10.0) -> dict:
    """Knee onset of each Fig. 4 car from its mean fade between 80k and 280k km.

    mean fade = e*(x2 - x1) + s*(x2 - tau)_+  ->  tau = x2 - (fade - e*(x2-x1))/s.
    Cars with < ``min_post_knee_km`` of implied post-knee driving are treated as
    right-censored at x2 - min_post_knee_km. Fits log tau ~ N(mu, sd) by MLE.
    Assumes every car shares the Fig. 3 car's pre-knee rate e.
    """
    fade = np.array([np.mean(q80 - q280) for q80, q280 in fig4])
    post = (fade - e_mean * (x2 - x1)) / s_mean
    censored = post < min_post_knee_km
    tau = np.where(censored, x2 - min_post_knee_km, x2 - post)
    lt = np.log(tau)

    def nll(p):
        mu, ls = p
        sd = np.exp(ls)
        obs = stats.norm.logpdf(lt[~censored], mu, sd).sum()
        cen = stats.norm.logsf(lt[censored], mu, sd).sum()
        return -(obs + cen)

    r = optimize.minimize(nll, [lt.mean(), np.log(lt.std() + 1e-3)], method="Nelder-Mead")
    mu, sd = r.x[0], float(np.exp(r.x[1]))
    return {"knee_pack_logsd": sd, "fleet_tau_km_median": float(np.exp(mu)),
            "per_car_tau_km": tau.round(1).tolist(), "per_car_censored": censored.tolist(),
            "per_car_mean_fade": fade.round(4).tolist()}


def calibrate(path) -> dict:
    km, Q, R = load_trajectories(path)
    h = fit_hinges(km, Q)
    cell = fit_cell_structure(h)
    res = fit_resistance(Q, R)
    pack = fit_pack_knee_spread(load_fig4(path), cell["e_mean_per_1000km"], cell["s_mean_per_1000km"])
    aging = {k: cell[k] for k in ("cell_cov", "knee_slope_ratio", "q0_cv")}
    aging["knee_onset_fade"] = float(1.0 - (cell["a_mean"] - cell["e_mean_per_1000km"]
                                             * (cell["tau_mean_km"] - cell["x0_km"])))
    aging["knee_pack_logsd"] = pack["knee_pack_logsd"]
    aging.update({k: res[k] for k in ("r0_cv", "resistance_growth")})
    aging = {k: (round(v, 5) if isinstance(v, float) else v) for k, v in aging.items()}
    return {"source": "Zhou et al. 2026 Nature Energy, github.com/Rico-dicp/Ev-battery-cell-to-cell-inconsistency",
            "aging": aging, "ev_clock": cell, "resistance": res, "pack_knee": pack}


# ------------------------------------------------------------------ validation
def simulate_ev_packs(calib: dict, n_packs=2000, n_cells=95, km=None, seed=0):
    """Calibrated cells on the EV mileage clock: Q(x) for x in ``km``."""
    rng = np.random.default_rng(seed)
    ev = calib["ev_clock"]
    aging = AgingConfig(**{**{k: v for k, v in calib["aging"].items()},
                           "cell_cov": tuple(map(tuple, calib["aging"]["cell_cov"])),
                           "temp_sd_C": 2.0})
    km = np.arange(60.0, 420.0, 2.0) if km is None else np.asarray(km, float)
    sP = aging.knee_pack_logsd
    tau_fleet = calib["pack_knee"]["fleet_tau_km_median"]
    Qs = np.empty((n_packs, n_cells, km.size))
    for p in range(n_packs):
        d = draw_cell_parameters(aging, n_cells, rng)
        tau = tau_fleet * rng.lognormal(0.0, sP) * d["tau_rel"]
        a0 = ev["a_mean"] * d["q0"]
        e = ev["e_mean_per_1000km"]
        Qs[p] = (a0[:, None] - d["m"][:, None] * e * (km[None, :] - ev["x0_km"])
                 - d["kappa"][:, None] * e * np.maximum(km[None, :] - tau[:, None], 0.0))
    return km, Qs


def pack_metrics(Q):
    """sigma_SOH, beta_SOH = min/mean, z = (mean - min)/sd over the cell axis."""
    mean, sd, mn = Q.mean(axis=-2), Q.std(axis=-2), Q.min(axis=-2)
    return {"sigma_soh": sd, "beta_soh": mn / mean, "z_min": (mean - mn) / np.maximum(sd, 1e-12)}


def beta_life(km, Q, eol=EOL_SOH):
    """Paper's beta_life: life of the first cell to hit EOL / mean cell life."""
    below = Q < eol
    hit = below.any(axis=-1)
    idx = np.where(hit, below.argmax(axis=-1), km.size - 1)
    life = km[idx]
    ok = hit.all(axis=-1)
    return np.where(ok, life.min(axis=-1) / life.mean(axis=-1), np.nan)


def validate(calib: dict, path, n_packs=2000, seed=0) -> dict:
    km, Qs = simulate_ev_packs(calib, n_packs=n_packs, seed=seed)
    sim = pack_metrics(Qs)
    fig4 = load_fig4(path)
    fig5 = load_fig5(path)
    out = {}

    # Fig. 4 at 280k km: within-pack statistics of 12 cars
    i280 = np.argmin(abs(km - 280))
    d280 = pack_metrics(np.stack([q[1] for q in fig4])[:, :, None])
    out["fig4_280k"] = {k: {"data_median": float(np.median(d280[k])), "data_range": [float(d280[k].min()), float(d280[k].max())],
                            "model_median": float(np.median(sim[k][:, i280])),
                            "model_p10_p90": [float(np.percentile(sim[k][:, i280], 10)), float(np.percentile(sim[k][:, i280], 90))]}
                        for k in ("sigma_soh", "beta_soh", "z_min")}

    # Fig. 5 a/b: by mileage bin (held out)
    bins = np.arange(0, 400, 50)
    rows = []
    for key in ("sigma_soh", "beta_soh"):
        df = fig5[key]
        df = df.assign(bin=(df.km // 50) * 50)
        for b in bins:
            sel = df[df.bin == b]
            if len(sel) < 20:
                continue
            m = (km >= b) & (km < b + 50)
            if not m.any():
                continue
            rows.append({"metric": key, "km_bin": f"{b}-{b + 50}k", "data_mean": float(sel[key].mean()),
                         "data_sd": float(sel[key].std()), "model_mean": float(sim[key][:, m].mean()),
                         "model_sd": float(sim[key][:, m].mean(axis=1).std())})
    out["fig5_by_mileage"] = rows

    # Fig. 5c: beta_life (held out)
    bl = beta_life(km, Qs)
    data_bl = fig5["beta_life"].beta_life.to_numpy(float)
    out["fig5c_beta_life"] = {"data_mean": float(data_bl.mean()), "data_sd": float(data_bl.std()),
                              "data_range": [float(data_bl.min()), float(data_bl.max())],
                              "model_mean": float(np.nanmean(bl)), "model_sd": float(np.nanstd(bl)),
                              "model_p10_p90": [float(np.nanpercentile(bl, 10)), float(np.nanpercentile(bl, 90))]}
    out["_sim"] = (km, Qs)
    return out


def fit_kappa_spread_scale(calib: dict, path, n_packs=400, seed=1, lo=0.0, hi=1.0, iters=10) -> float:
    """Shrink post-knee slope spread until model mean beta_life = data mean.

    Linear post-knee extrapolation of each cell over-spreads beyond ~300k km
    (the fleet's sigma_SOH levels off). beta_life is the one target used here;
    the Fig. 5a/b curves stay held out.
    """
    target = float(load_fig5(path)["beta_life"].beta_life.mean())

    def model_bl(scale):
        c = json.loads(json.dumps(calib))
        c["aging"]["kappa_spread_scale"] = scale
        km, Qs = simulate_ev_packs(c, n_packs=n_packs, seed=seed)
        return float(np.nanmean(beta_life(km, Qs)))

    if model_bl(lo) < target:      # even no slope spread is too pessimistic
        return lo
    for _ in range(iters):
        mid = 0.5 * (lo + hi)
        lo, hi = (mid, hi) if model_bl(mid) > target else (lo, mid)
    return round(0.5 * (lo + hi), 3)


def save_calibration(calib: dict, path) -> None:
    Path(path).write_text(json.dumps(calib, indent=2))
