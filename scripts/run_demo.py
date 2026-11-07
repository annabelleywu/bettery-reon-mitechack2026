"""End-to-end demo: learn the fault NHPP, then value cell-level bypass.

    python scripts/run_demo.py            # writes figures + summary to outputs/
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from reon_model import (  # noqa: E402
    FEATURES, HazardConfig, PackConfig, PoissonIntensityGLM, bypass_survival, compare,
    fit_gradient_boosted_intensity, fixed_string_survival, poisson_deviance, simulate,
)

OUT = Path(__file__).resolve().parents[1] / "outputs"
OUT.mkdir(exist_ok=True)
FIXED, BYPASS = "#8a8f98", "#1fa83a"


def train_test_split_by_pack(rows, frac=0.7, seed=0):
    packs = np.unique(rows["pack"])
    rng = np.random.default_rng(seed)
    train_packs = rng.choice(packs, int(frac * packs.size), replace=False)
    m = np.isin(rows["pack"], train_packs)
    return ({k: v[m] for k, v in rows.items()}, {k: v[~m] for k, v in rows.items()})


def main():
    lines = ["# REON fault-intensity model and value demo\n",
             "All inputs are placeholder assumptions (see `reon_model/simulate.py`).\n"]
    pack = PackConfig()
    truth = HazardConfig()

    # ------------------------------------------------------------------ 1. learn
    # "Fleet telemetry": 120 monitored packs x 96 cells x 10 years (synthetic,
    # with a known ground-truth hazard so we can check the learner).
    fleet = simulate("bypass", n_packs=120, pack=PackConfig(years=10.0), hazard=truth,
                     seed=11, record_rows=True)
    train, test = train_test_split_by_pack(fleet.rows)
    glm = PoissonIntensityGLM(feature_names=FEATURES).fit(train["X"], train["events"], train["exposure"])
    lrt = glm.lrt_vs_homogeneous()
    gbm = fit_gradient_boosted_intensity(train["X"], train["events"], train["exposure"])

    mu_glm = glm.predict_mean(test["X"], test["exposure"])
    mu_gbm = gbm.predict(test["X"]) * test["exposure"]
    mu_hom = glm.homogeneous_rate_ * test["exposure"]
    lines += ["## 1. Learned fault intensity  lambda_i(t) = lambda_0 exp(beta . x_i(t))\n",
              f"Training rows: {train['events'].size:,} cell-months, {int(train['events'].sum())} faults.\n",
              "```", glm.summary(), "```",
              f"True: log lambda_0 = {np.log(truth.base_rate):.4f}, "
              + ", ".join(f"{f} = {truth.coef[f]}" for f in FEATURES) + "\n",
              f"Likelihood-ratio test vs simple Poisson (all lambdas equal): "
              f"LR = {lrt['lr_stat']:.1f}, df = {lrt['df']}, p = {lrt['p_value']:.2e}\n",
              "Held-out mean Poisson deviance (lower is better, packs not seen in training):\n",
              "| model | deviance |", "|---|---|",
              f"| simple Poisson (one lambda) | {poisson_deviance(test['events'], mu_hom):.5f} |",
              f"| NHPP GLM | {poisson_deviance(test['events'], mu_glm):.5f} |",
              f"| NHPP gradient boosting | {poisson_deviance(test['events'], mu_gbm):.5f} |\n"]

    # Reduction check: same pipeline on a fleet whose cells truly share one rate.
    hom_rate = 0.004
    hom = simulate("bypass", n_packs=120, pack=PackConfig(years=10.0),
                   hazard=HazardConfig.homogeneous(hom_rate), seed=12, record_rows=True)
    g0 = PoissonIntensityGLM(feature_names=FEATURES).fit(hom.rows["X"], hom.rows["events"], hom.rows["exposure"])
    l0 = g0.lrt_vs_homogeneous()
    lines += ["### Reduction check: fleet with equal lambdas\n",
              f"True rate {hom_rate}; simple-Poisson MLE sum(y)/sum(e) = {g0.homogeneous_rate_:.5f}; "
              f"GLM slopes = {np.round(g0.coef_, 3).tolist()} (SE {np.round(g0.se_[1:], 3).tolist()}); "
              f"LRT p = {l0['p_value']:.3f} -> no evidence against the simple Poisson process.\n"]

    # ------------------------------------------------------------- 2. value it
    res = compare(n_packs=500, pack=pack, hazard=truth, seed=0)
    f, b = res["fixed"], res["bypass"]
    t = f.t

    def pct(a, q):
        a = np.where(np.isfinite(a), a, pack.years)
        return np.percentile(a, q)

    rows = [
        ("Retirement year (retention < 70%)", pct(f.retirement_year, [10, 50, 90]), pct(b.retirement_year, [10, 50, 90])),
        ("Lifetime delivered energy (MWh)", np.percentile(f.delivered_mwh, [10, 50, 90]), np.percentile(b.delivered_mwh, [10, 50, 90])),
        ("Service visits (outages) over 15 y", np.percentile(f.service_visits, [10, 50, 90]), np.percentile(b.service_visits, [10, 50, 90])),
        ("Hard cell faults over 15 y", np.percentile(f.faults, [10, 50, 90]), np.percentile(b.faults, [10, 50, 90])),
        ("Availability (%)", 100 * np.percentile(f.availability.mean(1), [10, 50, 90]), 100 * np.percentile(b.availability.mean(1), [10, 50, 90])),
    ]
    lines += [f"## 2. Fixed string vs. per-cell bypass ({pack.n_series}s, {pack.nameplate_kwh:.1f} kWh, "
              f"bypass headroom k = {pack.bypass_headroom}, 500 Monte Carlo packs)\n",
              "| metric | fixed P10 / P50 / P90 | bypass P10 / P50 / P90 |", "|---|---|---|"]
    for name, a, c in rows:
        lines.append(f"| {name} | {' / '.join(f'{x:.1f}' for x in a)} | {' / '.join(f'{x:.1f}' for x in c)} |")
    gain = b.delivered_mwh - f.delivered_mwh
    life = np.where(np.isfinite(b.retirement_year), b.retirement_year, pack.years) - \
        np.where(np.isfinite(f.retirement_year), f.retirement_year, pack.years)
    lines += ["", f"Paired difference (same initial cells): +{np.median(life):.2f} years of service "
              f"(P10 {np.percentile(life, 10):.2f}, P90 {np.percentile(life, 90):.2f}), "
              f"+{np.median(gain):.1f} MWh delivered (P10 {np.percentile(gain, 10):.1f}, P90 {np.percentile(gain, 90):.1f}).\n"]

    fig, ax = plt.subplots(1, 2, figsize=(12, 4.2))
    for r, c, lab in ((f, FIXED, "fixed string"), (b, BYPASS, f"per-cell bypass (k={pack.bypass_headroom})")):
        q = np.percentile(r.retention, [10, 50, 90], axis=0)
        ax[0].fill_between(t, q[0], q[2], color=c, alpha=0.25, lw=0)
        ax[0].plot(t, q[1], color=c, lw=2, label=f"{lab}, P50 with P10-P90")
    ax[0].axhline(pack.retirement_retention, color="k", ls="--", lw=1)
    ax[0].text(0.3, pack.retirement_retention + 0.01, "retirement threshold", fontsize=8)
    ax[0].set(xlabel="years in service", ylabel="usable energy / nameplate", title="System retention", ylim=(0.4, 1.02))
    ax[0].legend(fontsize=8, loc="lower left")
    bins = np.arange(0, pack.years + 0.5, 0.5)
    ax[1].hist(np.where(np.isfinite(f.retirement_year), f.retirement_year, pack.years),
               bins=bins, color=FIXED, alpha=0.8, label="fixed string")
    ax[1].hist(np.where(np.isfinite(b.retirement_year), b.retirement_year, pack.years),
               bins=bins, color=BYPASS, alpha=0.7, label="per-cell bypass")
    ax[1].set(xlabel="retirement year", ylabel="packs", title="When does the system fall below 70%?")
    ax[1].legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(OUT / "retention_and_retirement.png", dpi=150)
    plt.close(fig)

    # ------------------------------------------- 3. forward risk from the model
    # Take one pack at year 8, score each cell with the learned intensity, and
    # project the chance the system stays up over the next 24 months.
    k8 = 8 * pack.steps_per_year
    snap = simulate("bypass", n_packs=1, pack=PackConfig(years=8.0 + 1 / 12), hazard=truth, seed=21, record_rows=True)
    m = snap.rows["t"] == snap.t[k8]
    lam_cells = glm.predict_rate(snap.rows["X"][m])
    horizon = np.linspace(0, 2, 49)
    L = lam_cells[:, None] * horizon[None, :]          # held constant over the window
    s_fixed = fixed_string_survival(L)
    s_byp = {k: bypass_survival(L, k) for k in (1, 2, 4)}
    s_hom = np.exp(-glm.homogeneous_rate_ * lam_cells.size * horizon)
    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    ax.plot(horizon, s_fixed, color=FIXED, lw=2, label="fixed string: exp(-sum Lambda_i)")
    ax.plot(horizon, s_hom, color=FIXED, lw=1, ls=":", label="fixed string, simple Poisson (one lambda)")
    for k, s in s_byp.items():
        ax.plot(horizon, s, color=BYPASS, lw=1 + k / 2, alpha=0.5 + k / 8, label=f"bypass up to {k} cells")
    ax.set(xlabel="years from now", ylabel="P(no outage)", title="Outage risk for one pack at year 8", ylim=(0, 1.02))
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(OUT / "outage_risk_year8.png", dpi=150)
    plt.close(fig)
    top = np.argsort(lam_cells)[::-1][:5]
    lines += ["## 3. Early warning from the learned model (one pack at year 8)\n",
              f"Riskiest cells' predicted fault rates (per year): {np.round(lam_cells[top], 4).tolist()} "
              f"vs. pack median {np.median(lam_cells):.4f}.\n",
              f"P(no outage in next 12 months): fixed {np.interp(1, horizon, s_fixed):.3f}, "
              + ", ".join(f"bypass k={k} {np.interp(1, horizon, s):.3f}" for k, s in s_byp.items()) + "\n",
              "Figures: `retention_and_retirement.png`, `outage_risk_year8.png`.\n"]

    (OUT / "summary.md").write_text("\n".join(lines))
    print("\n".join(lines))


if __name__ == "__main__":
    main()
