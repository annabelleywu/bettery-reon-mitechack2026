"""Calibrate the aging model on Zhou et al. (2026) and validate it.

    ./scripts/fetch_paper_data.sh
    python scripts/calibrate.py

Writes data/calibration_zhou2026.json, outputs/calibration_report.md and
outputs/calibration_validation.png.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from reon_model.calibration import (  # noqa: E402
    beta_life, calibrate, fit_hinges, fit_kappa_spread_scale, load_fig5, load_trajectories,
    pack_metrics, save_calibration, simulate_ev_packs, validate,
)

DATA = ROOT / "data" / "paper" / "repo"
OUT = ROOT / "outputs"
GREEN, GREY, BLUE = "#1fa83a", "#8a8f98", "#2b6cb0"


def main():
    if not DATA.exists():
        sys.exit("Run ./scripts/fetch_paper_data.sh first.")
    OUT.mkdir(exist_ok=True)
    calib = calibrate(DATA)
    scale = fit_kappa_spread_scale(calib, DATA)
    calib["aging"]["kappa_spread_scale"] = scale
    as_fitted = json.loads(json.dumps(calib))
    as_fitted["aging"]["kappa_spread_scale"] = 1.0
    calib["aging_as_fitted"] = as_fitted["aging"]
    save_calibration(calib, ROOT / "data" / "calibration_zhou2026.json")

    val = {"beta_life_matched": validate(calib, DATA, n_packs=1500),
           "as_fitted": validate(as_fitted, DATA, n_packs=1500)}

    # ---------------------------------------------------------------- figure
    km_d, Q_d, _ = load_trajectories(DATA)
    h = fit_hinges(km_d, Q_d)
    f5 = load_fig5(DATA)
    fig, ax = plt.subplots(2, 2, figsize=(12, 8.5))
    a = ax[0, 0]
    a.plot(km_d, Q_d, color=GREY, lw=0.4, alpha=0.6)
    for j in h.sort_values("tau").index[[0, 47, 94]]:
        r = h.loc[j]
        a.plot(km_d, r.a - r.e * (km_d - r.x0) - r.s * np.maximum(km_d - r.tau, 0), color=GREEN, lw=1.5)
    a.set(title="Fig. 3g: 95 cells of one car (grey), hinge fits for 3 (green)",
          xlabel="mileage (10^3 km)", ylabel="normalised capacity")

    for a, key, title in ((ax[0, 1], "sigma_soh", "Cell spread sigma_SOH (held out)"),
                          (ax[1, 0], "beta_soh", "Weakest / average beta_SOH (held out)")):
        df = f5[key]
        a.scatter(df.km, df[key], s=2, color=GREY, alpha=0.4, label="Fig. 5: 19 cars")
        for name, col in (("as_fitted", BLUE), ("beta_life_matched", GREEN)):
            km, Qs = val[name]["_sim"]
            m = pack_metrics(Qs)[key]
            q = np.percentile(m, [10, 50, 90], axis=0)
            a.fill_between(km, q[0], q[2], color=col, alpha=0.15, lw=0)
            a.plot(km, q[1], color=col, lw=2, label=f"model ({name.replace('_', ' ')}), P10-P90")
        a.set(title=title, xlabel="mileage (10^3 km)", xlim=(25, 390))
        a.legend(fontsize=8)
    ax[1, 0].set_ylim(0.75, 1.0)

    a = ax[1, 1]
    data_bl = f5["beta_life"].beta_life.to_numpy()
    bins = np.linspace(0.6, 0.95, 36)
    for name, col in (("as_fitted", BLUE), ("beta_life_matched", GREEN)):
        km, Qs = val[name]["_sim"]
        bl = beta_life(km, Qs)
        a.hist(bl[np.isfinite(bl)], bins=bins, density=True, color=col, alpha=0.35, label=f"model ({name.replace('_', ' ')})")
    a.hist(data_bl, bins=bins, density=True, histtype="step", color="k", lw=1.5, label="Fig. 5c: 19 cars")
    a.set(title="beta_life = first cell to 85% / average cell life", xlabel="beta_life")
    a.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(OUT / "calibration_validation.png", dpi=150)
    plt.close(fig)

    # ---------------------------------------------------------------- report
    ag = calib["aging"]
    ev = calib["ev_clock"]
    pk = calib["pack_knee"]
    C = np.array(ag["cell_cov"])
    sd = np.sqrt(np.diag(C))
    corr = C / np.outer(sd, sd)
    L = ["# Aging calibration on Zhou et al. (2026)\n",
         "Data: `Source Data of Figures in Manuscript` from the paper's GitHub repo (MIT licence). "
         "NMC passenger-car cells, 95 in series; capacities are estimated from field signals.\n",
         "## Fitted from Fig. 3g/3h (one car, 95 cell trajectories, 74k-303k km)\n",
         f"Hinge fit per cell, Q = a - e(x - x0) - s(x - tau)+, median RMSE {ev['hinge_rmse_median']:.5f}.\n",
         "| parameter | value |", "|---|---|",
         f"| pre-knee fade rate e, mean | {ev['e_mean_per_1000km'] * 100:.4f} per 100k km |",
         f"| knee onset tau, mean | {ev['tau_mean_km']:.0f}k km |",
         f"| post-knee extra slope s, mean | {ev['s_mean_per_1000km'] * 100:.4f} per 100k km (= {ag['knee_slope_ratio']:.2f} x e) |",
         f"| cell-to-cell CV of e / tau / s | {sd[0]:.3f} / {sd[1]:.3f} / {sd[2]:.3f} |",
         f"| skew of e / tau / s | {' / '.join(f'{x:.2f}' for x in ev['skew_e_tau_s'])} |",
         f"| corr(e, tau), corr(e, s), corr(tau, s) | {corr[0, 1]:.2f}, {corr[0, 2]:.2f}, {corr[1, 2]:.2f} |",
         f"| BOL capacity CV | {ag['q0_cv']:.4f} |",
         f"| resistance CV / growth (R/R0 - 1 per unit fade) | {ag['r0_cv']:.3f} / {ag['resistance_growth']:.2f} |",
         f"| mean-cell fade at knee onset (vs nominal) | {ag['knee_onset_fade']:.3f} |\n",
         "## Fitted from Fig. 4 (12 cars, 95 cells, 80k and 280k km)\n",
         f"Knee onset per car from its mean fade (assuming the Fig. 3 car's rates): "
         f"{', '.join(f'{t:.0f}' + ('+' if c else '') for t, c in zip(pk['per_car_tau_km'], pk['per_car_censored']))}k km "
         f"(+ = censored). Log-normal MLE: median {pk['fleet_tau_km_median']:.0f}k km, between-pack log-sd {ag['knee_pack_logsd']:.3f}.\n",
         "## Post-knee spread\n",
         "Extrapolating each cell's post-knee line indefinitely over-spreads the pack beyond ~300k km "
         f"(the fleet's sigma_SOH levels off). One parameter, `kappa_spread_scale` = {scale}, shrinks the "
         "cell-to-cell spread of post-knee slopes so the model's mean beta_life matches Fig. 5c. "
         "Both variants are kept: `as_fitted` (scale 1) and `beta_life_matched` (default).\n",
         "## Validation\n"]
    for name in ("beta_life_matched", "as_fitted"):
        v = val[name]
        L += [f"### {name.replace('_', ' ')}\n", "| check | data | model |", "|---|---|---|"]
        for k, x in v["fig4_280k"].items():
            L.append(f"| Fig. 4 @280k km {k} (median) | {x['data_median']:.4f} (range {x['data_range'][0]:.4f}-{x['data_range'][1]:.4f}) "
                     f"| {x['model_median']:.4f} (P10-P90 {x['model_p10_p90'][0]:.4f}-{x['model_p10_p90'][1]:.4f}) |")
        for r in v["fig5_by_mileage"]:
            L.append(f"| Fig. 5 {r['metric']} {r['km_bin']} (held out) | {r['data_mean']:.4f} | {r['model_mean']:.4f} |")
        b = v["fig5c_beta_life"]
        L.append(f"| Fig. 5c beta_life mean{' (fitted target)' if name == 'beta_life_matched' else ' (held out)'} "
                 f"| {b['data_mean']:.3f} (sd {b['data_sd']:.3f}) | {b['model_mean']:.3f} (sd {b['model_sd']:.3f}) |\n")
    L += ["![validation](calibration_validation.png)\n",
          "## Not calibrated by this data\n",
          "- Stationary timeline: `k_cal`, `k_cyc` and the knee onset in years. The default transfers the knee by "
          f"matching the mean cell's fade at onset ({ag['knee_onset_fade']:.3f}); `run_demo.py` reports sensitivity to it.",
          "- Chemistry: these are NMC EV cells, and REON's EBS is sodium-ion. The spread structure is assumed to transfer.",
          "- Fault hazards: the repo has no fault events, so `HazardConfig` stays a placeholder.",
          "- Between-car differences in pre-knee rate are folded into the knee-onset spread."]
    (OUT / "calibration_report.md").write_text("\n".join(L))
    print("\n".join(L))


if __name__ == "__main__":
    main()
