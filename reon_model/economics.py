"""What cell-level control is worth to a Massachusetts C&I battery owner, in $ and CO2.

Revenue is computed for each simulated pack and each year of its service life, from the
simulated usable energy at the AC meter (Methodology v2, Sections 7-9). Per block:

* ConnectedSolutions Daily Dispatch pays $/kW on the average kW held over 2-3 h summer
  events (Mass Save / National Grid C&I program materials): rate x min(rated kW, E / event h).
* Demand charges (Eversource Greater Boston G-2) on the monthly 15-minute peak:
  12 x rate x realization x min(rated kW, E / peak h).
* Clean Peak certificates per MWh discharged in seasonal peak windows: clearing share x
  ACP ($65/MWh through 2032, $45 after, mass.gov) x multiplier x MWh, excluding
  ConnectedSolutions event days (stacking in the same hour is not confirmed).
* Battery losses bought at the energy price: MWh discharged x (1/RTE - 1) x price.
* Capex: installed $/kWh x nameplate x (1 + REON BMS overhead for cell-level) x (1 - ITC).

REON's CTO (hack Discord): REON's BMS costs ~3x a conventional BMS, which is 2-3% of system
cost, so the overhead is +4-6% of system cost (derived). Placeholders are marked below.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

LB_PER_T = 2204.62


@dataclass
class EconConfig:
    n_blocks: int = 2                    # REON EBS blocks at the site (2 x 30 kW / 60 kWh clears a >=50 kW C&I floor)
    ac_efficiency: float = 0.96          # inverter, DC to AC meter (placeholder)
    round_trip_efficiency: float = 0.88  # placeholder; ask REON
    cs_rate: float = 200.0               # $/kW-summer, ConnectedSolutions Daily Dispatch
    cs_event_hours: float = 3.0          # events are 2-3 h; 3 h is conservative
    cs_event_days: int = 45              # 30-60 events per summer
    dc_rate: float = 33.95               # $/kW-month, Eversource Greater Boston G-2 (Jul 2026); National Grid G-2: 15.06
    dc_hours: float = 2.0                # placeholder: duration of the site's monthly peak
    dc_realization: float = 0.75         # placeholder: share of theoretical demand savings realized
    cps_clear: float = 0.87              # CPECs clear ~87% of ACP (Modo Energy)
    cps_multiplier: float = 1.0          # merchant storage 1.0-2.0x; 1.0 conservative
    energy_price: float = 0.20           # $/kWh, National Grid commercial Basic Service ~21.7 c/kWh (Jan 2026)
    installed_cost: float = 600.0        # $/kWh installed (placeholder; small MA C&I installer range $500-800)
    bms_overhead: float = 0.04           # REON BMS overhead, share of system cost (REON CTO, derived 4-6%)
    itc: float = 0.30                    # federal investment tax credit (storage, FEOC caveat)
    discount_rate: float = 0.08
    start_year: int = 2027
    grid_co2_lb_per_mwh: float = 597.0   # ISO-NE 2024 average emission rate
    embodied_co2_kg_per_kwh: float = 80.0  # Fraunhofer 2025 LCA: sodium-ion 75-87 kg CO2e/kWh cell
    cell_kg_per_kwh: float = 7.0         # placeholder; ask REON
    horizon_years: int = 20              # years of storage service the owner needs

    def acp(self, year: int) -> float:
        return 65.0 if year <= 2032 else 45.0


def pack_value(res, pack, econ: EconConfig, cell_level: bool) -> dict:
    """Per-block economics for every simulated pack of one design. Returns arrays of shape (P,)."""
    P, K = res.energy_kwh.shape
    spy = pack.steps_per_year
    life_steps = np.where(np.isfinite(res.retirement_year), np.round(res.retirement_year * spy), K).astype(int)
    capex = econ.installed_cost * pack.nameplate_kwh * (1 + (econ.bms_overhead if cell_level else 0.0)) * (1 - econ.itc)
    out = {k: np.zeros(P) for k in ("npv", "mwh_ac", "cs1", "dc1", "cps1", "loss1", "net1")}
    out["payback"] = np.full(P, np.inf)
    out["capex"] = np.full(P, capex)
    for p in range(P):
        npv, cum = -capex, -capex
        for y in range(int(np.ceil(life_steps[p] / spy))):
            sl = slice(y * spy, min((y + 1) * spy, life_steps[p]))
            n = sl.stop - sl.start
            if n <= 0:
                break
            frac = n / spy
            E = res.energy_kwh[p, sl].mean() * econ.ac_efficiency
            A = res.availability[p, sl].mean()
            cs = econ.cs_rate * min(pack.rated_kw, E / econ.cs_event_hours) * A * (1.0 if frac >= 0.75 else frac)
            dc = 12 * frac * econ.dc_rate * econ.dc_realization * min(pack.rated_kw, E / econ.dc_hours) * A
            cps = (econ.cps_clear * econ.acp(econ.start_year + y) * econ.cps_multiplier * E / 1000
                   * max(pack.cycles_per_year - econ.cs_event_days, 0) * frac * A)
            mwh = E / 1000 * pack.cycles_per_year * frac * A
            loss = mwh * (1 / econ.round_trip_efficiency - 1) * econ.energy_price * 1000
            net = cs + dc + cps - loss
            out["mwh_ac"][p] += mwh
            npv += net / (1 + econ.discount_rate) ** (y + 1)
            prev, cum = cum, cum + net
            if not np.isfinite(out["payback"][p]) and cum >= 0:
                out["payback"][p] = y + (-prev / net if net > 0 else 0.0)
            if y == 0:
                out["cs1"][p], out["dc1"][p], out["cps1"][p], out["loss1"][p], out["net1"][p] = cs, dc, cps, loss, net
        out["npv"][p] = npv
    return out


def site_value(results: dict, pack, econ: EconConfig = EconConfig()) -> dict:
    """Site-level ($ for n_blocks) medians for both designs, paired NPV gain, and environment."""
    f = pack_value(results["fixed"], pack, econ, cell_level=False)
    c = pack_value(results["bypass"], pack, econ, cell_level=True)
    n = econ.n_blocks
    med = lambda x: float(np.median(x))
    d_npv = (c["npv"] - f["npv"]) * n
    d_mwh = (c["mwh_ac"] - f["mwh_ac"]) * n
    # mean service life over packs: life is counted in whole steps, so a median moves a month at a time
    life_f = float(np.mean(np.where(np.isfinite(results["fixed"].retirement_year), results["fixed"].retirement_year, pack.years)))
    life_c = float(np.mean(np.where(np.isfinite(results["bypass"].retirement_year), results["bypass"].retirement_year, pack.years)))
    kwh = pack.nameplate_kwh * n
    avoided_kwh = kwh * econ.horizon_years * (1 / max(life_f, 0.1) - 1 / max(life_c, 0.1))
    summary = {
        design: {key: med(v) * (n if key not in ("payback",) else 1) for key, v in vals.items()}
        for design, vals in (("fixed", f), ("bypass", c))
    }
    summary["delta"] = {
        "npv_p10": float(np.percentile(d_npv, 10)), "npv_p50": med(d_npv), "npv_p90": float(np.percentile(d_npv, 90)),
        "mwh_ac": med(d_mwh),
    }
    summary["environment"] = {
        "life_fixed": life_f, "life_bypass": life_c,
        "co2_operation_t": summary["delta"]["mwh_ac"] * econ.grid_co2_lb_per_mwh / LB_PER_T,
        "avoided_cell_kwh": avoided_kwh,
        "co2_cells_t": avoided_kwh * econ.embodied_co2_kg_per_kwh / 1000,
        "cells_kg": avoided_kwh * econ.cell_kg_per_kwh,
    }
    return summary


__all__ = ["EconConfig", "pack_value", "site_value"]
