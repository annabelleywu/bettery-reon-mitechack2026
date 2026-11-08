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
    h = x["value"]["horizon"]
    return (f"| {name} | {x['energy_gain']:+.1f}% | {x['life_gain']:+.1f}% | "
            f"{x['life_fixed']:.2f} / {x['life_bypass']:.2f} | "
            f"{h['npv_gain_mean']/1e3:+.1f}k ({h['npv_gain_p10']/1e3:+.1f}k, {h['npv_gain_p90']/1e3:+.1f}k) | "
            f"{x['value']['delta']['npv_p50']/1e3:+.1f}k |")


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
    d, h = x["value"]["delta"], x["value"]["horizon"]
    return (f"| {name} | {x['energy_gain']:+.1f}% | {x['life_gain']:+.1f}% | {x['life_fixed']:.2f} / {x['life_bypass']:.2f} | "
            f"{x['lost_to_fault_fixed']:.0%} / {x['lost_to_fault_bypass']:.0%} | {x['visits_fixed']:.1f} / {x['visits_bypass']:.1f} | "
            f"{h['blocks_fixed']:.2f} / {h['blocks_bypass']:.2f} | "
            f"{h['npv_gain_mean']/1e3:+.1f}k ({h['npv_gain_p10']/1e3:+.1f}k, {h['npv_gain_p90']/1e3:+.1f}k) |")


def grade_case(packs, aging_b, label, aging_f=None, econ=None):
    """REON built with more uneven (looser-binned, cheaper) cells against a fixed string with the paper's cells."""
    pack, econ = EBS, econ or EconConfig()
    cal = AgingConfig.from_calibration(CAL)
    rf = compare(n_packs=packs, pack=pack, aging=aging_f or cal, hazard=HazardConfig.off(), seed=0, policy=TEAM_POLICY)
    rb = compare(n_packs=packs, pack=pack, aging=aging_b, hazard=HazardConfig.off(), seed=0, policy=TEAM_POLICY)
    mixed = {"fixed": rf["fixed"], "bypass": rb["bypass"]}
    v = site_value(mixed, pack, econ)
    life = lambda x: np.where(np.isfinite(x.retirement_year), x.retirement_year, pack.years)
    return (f"| {label} | {100 * (np.mean(rb['bypass'].delivered_mwh) / np.mean(rf['fixed'].delivered_mwh) - 1):+.1f}% | "
            f"{100 * (np.mean(life(rb['bypass'])) / np.mean(life(rf['fixed'])) - 1):+.1f}% | "
            f"{v['horizon']['npv_gain_mean'] / 1e3:+.1f}k |")


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
    cases, faults, customers, grades = [], [], [], []

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
    cases.append(("Slower calendar aging (knee about 10 y, closer to REON's 10-y / 20,000-cycle cells)",
                  run(P, aging=dataclasses.replace(cal, k_cal=0.012))))
    cases.append(("Retire at 80%", run(P, pack=dataclasses.replace(pk, retirement_retention=0.80))))
    cases.append(("Retention vs own beginning of life (R_sys)", run(P, pack=dataclasses.replace(pk, retention_basis="bol"))))
    cases.append(("Switch loss 1.6% (0.5 mOhm at 100 A)", run(P, pack=dataclasses.replace(pk, switch_efficiency=0.984))))
    cases.append(("Switch loss 3.2% (1 mOhm at 100 A)", run(P, pack=dataclasses.replace(pk, switch_efficiency=0.968))))
    cases.append(("BMS overhead 6%", run(P, econ=EconConfig(bms_overhead=0.06))))
    cases.append(("Demand-charge capture 75% (instead of 50%)", run(P, econ=EconConfig(dc_realization=0.75))))
    cases.append(("Installed cost $800/kWh", run(P, econ=EconConfig(installed_cost=800.0))))
    cases.append(("No ITC (cells fail FEOC test)", run(P, econ=EconConfig(itc=0.0))))
    cases.append(("Horizon 15 years", run(P, econ=EconConfig(horizon_years=15))))

    customers.append(("Neighborhood grocer: Eversource G-1 demand option ($41.65/kW), 2 blocks",
                      run(P, econ=EconConfig(dc_rate=41.65))))
    customers.append(("Mid-size business: Eversource G-2 ($33.95/kW), 2 blocks (default)", base))
    customers.append(("Cold-storage warehouse: Eversource G-3 ($30.05/kW), 10 blocks",
                      run(P, econ=EconConfig(dc_rate=30.05, n_blocks=10))))
    customers.append(("Mid-size business on National Grid G-2 ($15.06/kW), 2 blocks", run(P, econ=EconConfig(dc_rate=15.06))))

    for sm in (1.5, 2.0, 2.5):
        grades.append(grade_case(P, dataclasses.replace(cal, spread_multiplier=sm),
                                 f"REON with cells {sm}x as uneven vs fixed string with the paper's cells"))

    for ppm in (10, 100, 1000):
        hz = HazardConfig.homogeneous(ppm * PPM)
        for mode, label in (("repair", "repair (14-day outage, $1,500 visit)"), ("retire", "retire the block")):
            faults.append((f"{ppm} ppm, base system: {label}",
                           run(PF, pack=dataclasses.replace(pk, on_string_fault=mode), hazard=hz)))

    v = base["value"]; f, b, env, hz = v["fixed"], v["bypass"], v["environment"], v["horizon"]
    hf, hb = hz["fixed"], hz["bypass"]
    ec = EconConfig()
    per100 = 100_000 / (pk.rated_kw * ec.n_blocks)      # sites per 100 MW of C&I storage
    d_mwh20 = hb["mwh_ac"] - hf["mwh_ac"]
    lines = [
        "# Value of cell-level control: Massachusetts C&I site",
        "",
        f"2 x REON EBS (60 kW / 120 kWh nominal; 250 cells per string, 10% backups), Eversource Greater Boston G-2, "
        f"from 2027. Team default: {H} packs per design; other cases: {P}; fault cases: {PF}. Identical cells in both "
        "designs. Inputs and sources: `docs/Methodology_v2.md`, `docs/Reliability_and_Customers_Research.md`, "
        "`reon_model/economics.py`.",
        "",
        "Energy and life: means over packs. **Money is compared over a 20-year service horizon**: when a block retires "
        "the owner buys a new one at that year's price (NLR, formerly NREL, 2025 mid-case decline) and ITC rate (full through 2033, "
        "75% in 2034, 50% in 2035, none after), pays fixed O&M of 4% of installed cost a year (NLR ATB 2025), and is "
        "credited straight-line salvage for the block in service at year 20. NPV gains are means of each pack's paired "
        "difference, with P10 and P90.",
        "",
        "## Team default, per site, over 20 years",
        "",
        "| | Fixed string | Cell-level control |",
        "|---|---|---|",
        f"| Blocks bought per position over 20 y | {hz['blocks_fixed']:.2f} | {hz['blocks_bypass']:.2f} |",
        f"| Installed cost, present value (after ITC) | ${hf['capex_pv']:,.0f} | ${hb['capex_pv']:,.0f} |",
        f"| Revenue, present value (ConnectedSolutions + demand charges + Clean Peak) | ${hf['revenue_pv']:,.0f} | ${hb['revenue_pv']:,.0f} |",
        f"| Fixed O&M, present value | ${hf['om_pv']:,.0f} | ${hb['om_pv']:,.0f} |",
        f"| Salvage at year 20, present value | ${hf['salvage_pv']:,.0f} | ${hb['salvage_pv']:,.0f} |",
        f"| **20-year NPV** | **${hf['npv']:,.0f}** | **${hb['npv']:,.0f}** |",
        f"| Simple payback (median) | {hz['payback_fixed']:.1f} y | {hz['payback_bypass']:.1f} y |",
        f"| Energy delivered over 20 y (AC) | {hf['mwh_ac']:.0f} MWh | {hb['mwh_ac']:.0f} MWh |",
        f"| Service life per block (mean) | {env['life_fixed']:.2f} y | {env['life_bypass']:.2f} y |",
        f"| Year 1: ConnectedSolutions / demand charges / Clean Peak / losses | ${f['cs1']:,.0f} / ${f['dc1']:,.0f} / ${f['cps1']:,.0f} / -${f['loss1']:,.0f} | ${b['cs1']:,.0f} / ${b['dc1']:,.0f} / ${b['cps1']:,.0f} / -${b['loss1']:,.0f} |",
        f"| Firm kW for 2 h at year 5 (per block) | {base['kw5_fixed']:.1f} | {base['kw5_bypass']:.1f} |",
        "",
        f"Lifetime energy gain per block **{base['energy_gain']:+.1f}%**, service life gain **{base['life_gain']:+.1f}%**. "
        f"**20-year NPV gain: ${hz['npv_gain_mean']:,.0f} per site** (P10 ${hz['npv_gain_p10']:,.0f}, P90 "
        f"${hz['npv_gain_p90']:,.0f}); over each design's own first life (no replacement) it is "
        f"${v['delta']['npv_p50']:,.0f}. Extra energy over 20 y: {d_mwh20:.1f} MWh. CO2 avoided over 20 y: "
        f"{d_mwh20 * ec.grid_co2_lb_per_mwh / 2204.62:.1f} t (operation) + {env['co2_cells_t']:.1f} t (cells not "
        f"manufactured). Cells kept out of waste: {env['cells_kg']:.0f} kg ({env['avoided_cell_kwh']:.0f} kWh). "
        f"beta_power at start of life (fixed): {base['bpow0']:.3f} (paper fleet 0.871).",
        "",
        f"**Scale-up, per 100 MW of C&I storage** ({per100:,.0f} two-block sites; Massachusetts had about 220 MW enrolled "
        f"in ConnectedSolutions in 2025): +${hz['npv_gain_mean'] * per100 / 1e6:.1f}M NPV, "
        f"+{d_mwh20 * per100 / 1000:.1f} GWh delivered and "
        f"{(d_mwh20 * ec.grid_co2_lb_per_mwh / 2204.62 + env['co2_cells_t']) * per100 / 1000:.1f} kt CO2 avoided over 20 years, "
        f"{env['cells_kg'] * per100 / 1000:.0f} t of cells not manufactured.",
        "",
        "## Customers (same battery, different site)",
        "",
        "| Customer | Lifetime energy gain | Life gain | Life fixed / cell-level (y) | 20-y NPV gain per site (P10, P90) | Own-life NPV gain |",
        "|---|---|---|---|---|---|",
    ] + [fmt_case(n, x) for n, x in customers] + [
        "",
        "## Cell grades: REON with looser-binned cells vs a fixed string with matched cells",
        "",
        "| Case | Lifetime energy | Life | 20-y NPV difference per site (same cell price) |",
        "|---|---|---|---|",
    ] + grades + [
        "",
        "Same cell price assumed. Cells are roughly 10-12% of installed cost (BNEF 2025: stationary-storage packs "
        "$70/kWh, average cells $74/kWh, against $600/kWh installed), so covering REON's 4% BMS overhead with cheaper "
        "cells alone needs a cell discount of roughly a third; any discount is added value.",
        "",
        "## All cases (no hard faults)",
        "",
        "| Case | Lifetime energy gain | Life gain | Life fixed / cell-level (y) | 20-y NPV gain per site (P10, P90) | Own-life NPV gain |",
        "|---|---|---|---|---|---|",
    ] + [fmt_case(n, x) for n, x in cases] + [
        "",
        f"## Hard cell faults ({PF} packs; same failure rate for every cell; REON switches a failed cell out and needs a "
        "visit only when more than 25 cells are out)",
        "",
        "| Case | Lifetime energy gain | Life gain | Life fixed / cell-level (y) | Blocks lost to a fault (fixed / cell-level) "
        "| Service visits per site over life (fixed / cell-level) | Blocks bought per position over 20 y (fixed / cell-level) "
        "| 20-y NPV gain per site (P10, P90) |",
        "|---|---|---|---|---|---|---|---|",
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
