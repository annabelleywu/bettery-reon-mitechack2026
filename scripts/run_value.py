"""Value of cell-level control for a Massachusetts C&I site: energy, life, kW, $ and CO2.

Writes outputs/value_summary.md. Faults are off (the paper's data has no fault events);
every case runs both designs on identical cells (common random numbers).

Energy and life gains are ratios of MEANS over the paired packs. Service life is counted in
whole months, so a median ratio jumps by about a point when the median pack crosses a month;
means converge about twice as fast (see docs/Methodology_v2.md, Section 10).

    python scripts/run_value.py                                       # headline 2000, sweeps 600, faults 1000
    python scripts/run_value.py --packs 40 --faultpacks 40 --headline 40  # quick check
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
# REON EBS block: 30 kW / 60 kWh nominal. REON (Tim Ren, Nov 7): 200-300 cells in series per string, about 10% of
# them redundant backups. So 250 cells x 3.1 V x 77.4 Ah = 60 kWh, with headroom k = 25. Same cells in both designs.
EBS = PackConfig(years=20, n_series=250, cell_ah=60000 / (250 * 3.1), bypass_headroom=25)
EBS_V2 = PackConfig(years=20, cell_ah=60000 / (96 * 3.1))           # previous setup: 96 cells, k = 4
OUT = pathlib.Path(__file__).resolve().parents[1] / "outputs" / "value_summary.md"

BYPASS_ONLY = ControlPolicy()          # bypass on empty and on fault
REST_POLICY = ControlPolicy(rest_count=2, rest_by="remaining_life", rest_threshold=0.20, rest_stop_health=0.85)
TEAM_POLICY = BYPASS_ONLY              # v3: REON improves system life, not cell life, so plain bypass is the headline
PPM = 1e-6


def run(packs, pack=None, aging=None, policy=TEAM_POLICY, econ=None, hazard=None, seed=0):
    pack = pack or EBS
    aging = aging or AgingConfig.from_calibration(CAL)
    econ = econ or EconConfig()
    r = compare(n_packs=packs, pack=pack, aging=aging, hazard=hazard or HazardConfig.off(), seed=seed, policy=policy)
    f, b = r["fixed"], r["bypass"]
    life = lambda x: np.where(np.isfinite(x.retirement_year), x.retirement_year, pack.years)
    v = site_value(r, pack, econ)
    k5 = 5 * pack.steps_per_year
    return {
        "energy_gain": 100 * (np.mean(b.delivered_mwh) / np.mean(f.delivered_mwh) - 1),
        "life_gain": 100 * (np.mean(life(b)) / np.mean(life(f)) - 1),
        "life_fixed": float(np.mean(life(f))), "life_bypass": float(np.mean(life(b))),
        "life_gain_p10": float(np.percentile(life(b) - life(f), 10)),
        "life_gain_p90": float(np.percentile(life(b) - life(f), 90)),
        "lost_to_fault_fixed": float(np.mean(f.retired_by_fault)), "lost_to_fault_bypass": float(np.mean(b.retired_by_fault)),
        "visits_fixed": float(np.mean(f.service_visits)) * econ.n_blocks, "visits_bypass": float(np.mean(b.service_visits)) * econ.n_blocks,
        "kw5_fixed": float(np.median(f.firm_kw[:, k5])), "kw5_bypass": float(np.median(b.firm_kw[:, k5])),
        "bpow0": float(np.nanmedian(f.beta_power[:, 0])),
        "value": v,
    }


def fmt_case(name, x):
    d = x["value"]["delta"]
    return (f"| {name} | {x['energy_gain']:+.1f}% | {x['life_gain']:+.1f}% | "
            f"{x['life_fixed']:.2f} / {x['life_bypass']:.2f} | "
            f"{d['npv_p50']/1e3:+.1f}k ({d['npv_p10']/1e3:+.1f}k, {d['npv_p90']/1e3:+.1f}k) |")


def reliability_table(n=250, k=25, years=(1, 10)):
    """Chance that a block is stopped by a hard cell fault: fixed string (any fault) vs k backups (more than k)."""
    from math import exp, factorial
    rows = ["| Per-cell failure rate | " + " | ".join(f"Fixed string, {y} y" for y in years) + " | "
            + " | ".join(f"Cell-level ({k} backups), {y} y" for y in years) + " |",
            "|---|" + "---|" * (2 * len(years))]
    for ppm in (10, 100, 1000):
        r = ppm * PPM
        fx = [1 - (1 - r) ** (n * y) for y in years]
        lam = [n * r * y for y in years]       # expected faults (failed cells are replaced at a visit)
        cl = [1 - sum(exp(-m) * m ** j / factorial(j) for j in range(k + 1)) for m in lam]
        rows.append(f"| {ppm} ppm per cell-year | " + " | ".join(f"{x:.1%}" for x in fx) + " | "
                    + " | ".join("about 0" if x < 1e-9 else (f"{x:.1e}" if x < 1e-3 else f"{x:.1%}") for x in cl) + " |")
    return rows


def fmt_fault(name, x):
    d = x["value"]["delta"]
    return (f"| {name} | {x['energy_gain']:+.1f}% | {x['life_gain']:+.1f}% | {x['life_fixed']:.2f} / {x['life_bypass']:.2f} | "
            f"{x['lost_to_fault_fixed']:.0%} / {x['lost_to_fault_bypass']:.0%} | {x['visits_fixed']:.1f} / {x['visits_bypass']:.1f} | "
            f"{d['npv_p50']/1e3:+.1f}k ({d['npv_p10']/1e3:+.1f}k, {d['npv_p90']/1e3:+.1f}k) |")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--packs", type=int, default=600, help="packs per design for the sweep cases")
    ap.add_argument("--faultpacks", type=int, default=1000, help="packs per design for the fault cases")
    ap.add_argument("--headline", type=int, default=2000, help="packs per design for the team default")
    args = ap.parse_args()
    P, PF, H = args.packs, args.faultpacks, args.headline
    t0 = time.time()
    cal = AgingConfig.from_calibration(CAL)
    pk = EBS
    cases, faults = [], []

    base = run(H)
    cases.append(("**Team default**: bypass on empty and on fault, 250 cells, k = 25 (10% backups), no hard faults", base))
    for k in (0, 5, 12, 50, 125, 249):
        cases.append((f"k = {k} of 250", run(P, pack=dataclasses.replace(pk, bypass_headroom=k))))
    cases.append(("Previous setup: 96 cells, k = 4", run(P, pack=EBS_V2)))
    for sm in (0.5, 2.0, 3.0):
        cases.append((f"Spread {sm}x", run(P, aging=dataclasses.replace(cal, spread_multiplier=sm))))
    cases.append(("Early-knee outliers 5% (knee x0.8)", run(P, aging=dataclasses.replace(cal, outlier_fraction=0.05))))
    cases.append(("Add resting (2 lowest remaining-life cells, before knee)", run(P, policy=REST_POLICY)))
    cyc = dataclasses.replace(cal, k_cal=0.005, k_cyc=4e-5)
    cases.append(("Cycle-dominated aging", run(P, aging=cyc)))
    cases.append(("Cycle-dominated aging + resting", run(P, aging=cyc, policy=REST_POLICY)))
    cases.append(("Retire at 80%", run(P, pack=dataclasses.replace(pk, retirement_retention=0.80))))
    cases.append(("Retention vs own beginning of life (R_sys)", run(P, pack=dataclasses.replace(pk, retention_basis="bol"))))
    cases.append(("Switch loss 1.6% (0.5 mOhm at 100 A)", run(P, pack=dataclasses.replace(pk, switch_efficiency=0.984))))
    cases.append(("BMS overhead 6%", run(P, econ=EconConfig(bms_overhead=0.06))))
    cases.append(("National Grid G-2 ($15.06/kW-month)", run(P, econ=EconConfig(dc_rate=15.06))))
    cases.append(("No ITC (cells fail FEOC test)", run(P, econ=EconConfig(itc=0.0))))

    for ppm in (10, 100, 1000):
        hz = HazardConfig.homogeneous(ppm * PPM)
        for mode, label in (("repair", "repair (14-day outage, $1,500 visit)"), ("retire", "retire the block")):
            faults.append((f"{ppm} ppm, base system: {label}",
                           run(PF, pack=dataclasses.replace(pk, on_string_fault=mode), hazard=hz)))

    v = base["value"]; f, b, env = v["fixed"], v["bypass"], v["environment"]
    lines = [
        "# Value of cell-level control: Massachusetts C&I site",
        "",
        f"2 x REON EBS (60 kW / 120 kWh nominal; 250 cells per string, 10% backups), Eversource Greater Boston G-2, "
        f"from 2027. Team default: {H} packs per design; other cases: {P}. Identical cells in both designs. Inputs and "
        "sources: `docs/Methodology_v2.md`, `docs/Reliability_and_Customers_Research.md`, `reon_model/economics.py`.",
        "",
        "Energy and life: means over packs. Dollars: medians over packs; NPV gain is the median of each pack's "
        "paired difference.",
        "",
        "## Team default, per site",
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
        f"| Service life (mean) | {env['life_fixed']:.2f} y | {env['life_bypass']:.2f} y |",
        f"| Firm kW for 2 h at year 5 (per block) | {base['kw5_fixed']:.1f} | {base['kw5_bypass']:.1f} |",
        "",
        f"Lifetime energy gain **{base['energy_gain']:+.1f}%**, service life gain **{base['life_gain']:+.1f}%** "
        f"(per pack: P10 {base['life_gain_p10']:+.2f} y, P90 {base['life_gain_p90']:+.2f} y). "
        f"NPV gain from cell-level control: **${v['delta']['npv_p50']:,.0f}** per site "
        f"(P10 ${v['delta']['npv_p10']:,.0f}, P90 ${v['delta']['npv_p90']:,.0f}). "
        f"Extra energy {v['delta']['mwh_ac']:.1f} MWh. CO2 avoided: {env['co2_operation_t']:.1f} t (operation) + "
        f"{env['co2_cells_t']:.1f} t (cells not manufactured over 20 y). Cells kept out of waste: {env['cells_kg']:.0f} kg "
        f"({env['avoided_cell_kwh']:.0f} kWh). beta_power at start of life (fixed): {base['bpow0']:.3f} (paper fleet 0.871).",
        "",
        "## All cases (no hard faults)",
        "",
        "| Case | Lifetime energy gain | Life gain | Life fixed / cell-level (y) | NPV gain per site (P10, P90) |",
        "|---|---|---|---|---|",
    ] + [fmt_case(n, x) for n, x in cases] + [
        "",
        f"## Hard cell faults ({PF} packs; same failure rate for every cell; REON switches a failed cell out and needs a "
        "visit only when more than 25 cells are out)",
        "",
        "| Case | Lifetime energy gain | Life gain | Life fixed / cell-level (y) | Blocks lost to a fault (fixed / cell-level) "
        "| Service visits per site over life (fixed / cell-level) | NPV gain per site (P10, P90) |",
        "|---|---|---|---|---|---|---|",
    ] + [fmt_fault(n, x) for n, x in faults] + [
        "",
        "Chance that a fault stops a 250-cell block (arithmetic, no aging):",
        "",
    ] + reliability_table() + [
        "",
        f"Run time {time.time() - t0:.0f} s.",
    ]
    OUT.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
