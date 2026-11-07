"""Value of cell-level control for a Massachusetts C&I site: energy, life, kW, $ and CO2.

Writes outputs/value_summary.md. Faults are off (the paper's data has no fault events);
every case runs both designs on identical cells (common random numbers).

    python scripts/run_value.py            # 300 packs
    python scripts/run_value.py --packs 60 # quick check
"""
from __future__ import annotations

import argparse
import dataclasses
import pathlib
import sys
import time

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from reon_model.control import ControlPolicy  # noqa: E402
from reon_model.economics import EconConfig, site_value  # noqa: E402
from reon_model.simulate import AgingConfig, HazardConfig, PackConfig, compare  # noqa: E402

CAL = pathlib.Path(__file__).resolve().parents[1] / "data" / "calibration_zhou2026.json"
OUT = pathlib.Path(__file__).resolve().parents[1] / "outputs" / "value_summary.md"

TEAM_POLICY = ControlPolicy(rest_count=2, rest_by="remaining_life", rest_threshold=0.20, rest_stop_health=0.85)
BYPASS_ONLY = ControlPolicy()


def run(packs, pack=None, aging=None, policy=TEAM_POLICY, econ=None, hazard=None, seed=0):
    pack = pack or PackConfig(years=20)
    aging = aging or AgingConfig.from_calibration(CAL)
    econ = econ or EconConfig()
    r = compare(n_packs=packs, pack=pack, aging=aging, hazard=hazard or HazardConfig.off(), seed=seed, policy=policy)
    f, b = r["fixed"], r["bypass"]
    life = lambda x: np.where(np.isfinite(x.retirement_year), x.retirement_year, pack.years)
    v = site_value(r, pack, econ)
    k5 = 5 * pack.steps_per_year
    return {
        "energy_gain": 100 * (np.median(b.delivered_mwh) / np.median(f.delivered_mwh) - 1),
        "life_gain": 100 * (np.median(life(b)) / np.median(life(f)) - 1),
        "life_fixed": float(np.median(life(f))), "life_bypass": float(np.median(life(b))),
        "kw5_fixed": float(np.median(f.firm_kw[:, k5])), "kw5_bypass": float(np.median(b.firm_kw[:, k5])),
        "bpow0": float(np.nanmedian(f.beta_power[:, 0])),
        "value": v,
    }


def fmt_case(name, x):
    d = x["value"]["delta"]
    return (f"| {name} | {x['energy_gain']:+.1f}% | {x['life_gain']:+.1f}% | "
            f"{x['life_fixed']:.2f} / {x['life_bypass']:.2f} | "
            f"{d['npv_p50']/1e3:+.1f}k ({d['npv_p10']/1e3:+.1f}k, {d['npv_p90']/1e3:+.1f}k) |")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--packs", type=int, default=300)
    args = ap.parse_args()
    P = args.packs
    t0 = time.time()
    cal = AgingConfig.from_calibration(CAL)
    pk = PackConfig(years=20)
    cases = []

    base = run(P)
    cases.append(("**Team default**: bypass on empty + rest before knee, k = 4", base))
    cases.append(("Bypass on empty only, k = 4", run(P, policy=BYPASS_ONLY)))
    for k in (0, 2, 8, 16, 32, 95):
        cases.append((f"Bypass only, k = {k}", run(P, pack=dataclasses.replace(pk, bypass_headroom=k), policy=BYPASS_ONLY)))
    for s in (0.5, 1.5, 2.0, 3.0):
        cases.append((f"Spread {s}x", run(P, aging=dataclasses.replace(cal, spread_multiplier=s))))
    cases.append(("Early-knee outliers 5% (knee x0.8)", run(P, aging=dataclasses.replace(cal, outlier_fraction=0.05))))
    for x in (0.0, 0.3, 0.5):
        cases.append((f"Rest threshold {x:.0%}", run(P, policy=dataclasses.replace(TEAM_POLICY, rest_threshold=x))))
    cases.append(("Rest all life (no stop)", run(P, policy=dataclasses.replace(TEAM_POLICY, rest_stop_health=0.0))))
    cyc = dataclasses.replace(cal, k_cal=0.005, k_cyc=4e-5)
    cases.append(("Cycle-dominated aging, bypass only", run(P, aging=cyc, policy=BYPASS_ONLY)))
    cases.append(("Cycle-dominated aging, rest before knee", run(P, aging=cyc)))
    cases.append(("Retire at 80%", run(P, pack=dataclasses.replace(pk, retirement_retention=0.80))))
    cases.append(("Retention vs own beginning of life (R_sys)", run(P, pack=dataclasses.replace(pk, retention_basis="bol"))))
    cases.append(("BMS overhead 6%", run(P, econ=EconConfig(bms_overhead=0.06))))
    cases.append(("National Grid G-2 ($15.06/kW-month)", run(P, econ=EconConfig(dc_rate=15.06))))
    cases.append(("Sudden faults on (placeholder rates)", run(P, hazard=HazardConfig())))

    v = base["value"]; f, b, env = v["fixed"], v["bypass"], v["environment"]
    lines = [
        "# Value of cell-level control: Massachusetts C&I site",
        "",
        f"2 x REON EBS (60 kW / 120 kWh nominal), Eversource Greater Boston G-2, from 2027. {P} packs per design, "
        "identical cells in both designs, sudden faults off. Inputs and sources: `docs/Methodology_v2.md`, `reon_model/economics.py`.",
        "",
        "## Team default, per site (medians)",
        "",
        "| | Fixed string | Cell-level control |",
        "|---|---|---|",
        f"| Installed cost after ITC | ${f['capex']:,.0f} | ${b['capex']:,.0f} |",
        f"| Year 1: ConnectedSolutions | ${f['cs1']:,.0f} | ${b['cs1']:,.0f} |",
        f"| Year 1: demand charges | ${f['dc1']:,.0f} | ${b['dc1']:,.0f} |",
        f"| Year 1: Clean Peak | ${f['cps1']:,.0f} | ${b['cps1']:,.0f} |",
        f"| Year 1: battery losses | -${f['loss1']:,.0f} | -${b['loss1']:,.0f} |",
        f"| Year 1 net | ${f['net1']:,.0f} | ${b['net1']:,.0f} |",
        f"| Simple payback | {f['payback']:.2f} y | {b['payback']:.2f} y |",
        f"| NPV over service life | ${f['npv']:,.0f} | ${b['npv']:,.0f} |",
        f"| Energy delivered (AC) | {f['mwh_ac']:.0f} MWh | {b['mwh_ac']:.0f} MWh |",
        f"| Service life | {env['life_fixed']:.2f} y | {env['life_bypass']:.2f} y |",
        f"| Firm kW for 2 h at year 5 (per block) | {base['kw5_fixed']:.1f} | {base['kw5_bypass']:.1f} |",
        "",
        f"NPV gain from cell-level control: **${v['delta']['npv_p50']:,.0f}** per site "
        f"(P10 ${v['delta']['npv_p10']:,.0f}, P90 ${v['delta']['npv_p90']:,.0f}). "
        f"Extra energy {v['delta']['mwh_ac']:.1f} MWh. CO2 avoided: {env['co2_operation_t']:.1f} t (operation) + "
        f"{env['co2_cells_t']:.1f} t (cells not manufactured over 20 y). Cells kept out of waste: {env['cells_kg']:.0f} kg "
        f"({env['avoided_cell_kwh']:.0f} kWh). beta_power at start of life (fixed): {base['bpow0']:.3f} (paper fleet 0.871).",
        "",
        "## All cases",
        "",
        "| Case | Lifetime energy gain | Life gain | Life fixed / cell-level (y) | NPV gain per site (P10, P90) |",
        "|---|---|---|---|---|",
    ] + [fmt_case(n, x) for n, x in cases] + [
        "",
        f"Run time {time.time() - t0:.0f} s.",
    ]
    OUT.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
