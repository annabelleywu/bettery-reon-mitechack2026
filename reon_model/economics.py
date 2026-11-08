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
    dc_rate: float = 33.95               # $/kW-month, Eversource Greater Boston G-2 (rate summary eff. Sep 1, 2026); National Grid G-2: 15.06
    dc_hours: float = 2.0                # placeholder: duration of the site's monthly peak
    dc_realization: float = 0.50         # assumed share of theoretical demand savings realized (conservative; 75% sensitivity)
    cps_clear: float = 0.87              # CPECs clear ~87% of ACP (Modo Energy)
    cps_multiplier: float = 1.0          # merchant storage 1.0-2.0x; 1.0 conservative
    energy_price: float = 0.20           # $/kWh, National Grid commercial Basic Service ~21.7 c/kWh (Jan 2026)
    installed_cost: float = 600.0        # $/kWh installed (placeholder; small MA C&I installer range $500-800)
    bms_overhead: float = 0.04           # REON BMS overhead, share of system cost (REON CTO, derived 4-6%)
    itc: float = 0.30                    # federal investment tax credit (storage, FEOC caveat)
    discount_rate: float = 0.08
    visit_cost: float = 1500.0           # $ per service visit to replace a failed cell or module (placeholder; $500-3,000)
    start_year: int = 2027
    grid_co2_lb_per_mwh: float = 597.0   # ISO-NE 2024 average emission rate
    embodied_co2_kg_per_kwh: float = 80.0  # Fraunhofer 2024 LCA: sodium-ion 75-87 kg CO2e/kWh cell
    cell_kg_per_kwh: float = 7.0         # placeholder; ask REON
    horizon_years: int = 20              # years of storage service the owner needs
    fom_frac: float = 0.04               # fixed O&M per year, share of installed cost (NREL/NLR ATB 2025, commercial battery storage; 2024 edition: 2.5%)
    # NREL "Cost Projections for Utility-Scale Battery Storage: 2025 Update" (Cole, Ramasamy, Turan), mid case,
    # cost relative to 2024: used for the price of replacement blocks bought later in the horizon
    cost_curve: tuple = ((2024, 1.00), (2030, 0.84), (2035, 0.73), (2040, 0.66), (2050, 0.53))

    def itc_rate(self, year: int) -> float:
        """Storage ITC by year construction begins (OBBBA keeps the IRA schedule for storage): full rate through
        2033, 75% of it in 2034, 50% in 2035, none after."""
        return self.itc * (1.0 if year <= 2033 else 0.75 if year == 2034 else 0.5 if year == 2035 else 0.0)

    def cost_factor(self, year: float) -> float:
        """Installed cost in ``year`` relative to the start year (NREL mid-case decline)."""
        xs, ys = zip(*self.cost_curve)
        return float(np.interp(year, xs, ys) / np.interp(self.start_year, xs, ys))

    def acp(self, year: int) -> float:
        return 65.0 if year <= 2032 else 45.0


def pack_value(res, pack, econ: EconConfig, cell_level: bool) -> dict:
    """Per-block economics for every simulated pack of one design. Returns arrays of shape (P,)."""
    P, K = res.energy_kwh.shape
    spy = pack.steps_per_year
    life_steps = np.where(np.isfinite(res.retirement_year), np.round(res.retirement_year * spy), K).astype(int)
    capex = econ.installed_cost * pack.nameplate_kwh * (1 + (econ.bms_overhead if cell_level else 0.0)) * (1 - econ.itc)
    out = {k: np.zeros(P) for k in ("npv", "mwh_ac", "cs1", "dc1", "cps1", "loss1", "net1", "visit_cost")}
    vk = getattr(res, "visits_by_step", None)
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
            visit = econ.visit_cost * (vk[p, sl].sum() if vk is not None else 0.0)
            out["visit_cost"][p] += visit
            net = cs + dc + cps - loss - visit
            out["mwh_ac"][p] += mwh
            npv += net / (1 + econ.discount_rate) ** (y + 1)
            prev, cum = cum, cum + net
            if not np.isfinite(out["payback"][p]) and cum >= 0:
                out["payback"][p] = y + (-prev / net if net > 0 else 0.0)
            if y == 0:
                out["cs1"][p], out["dc1"][p], out["cps1"][p], out["loss1"][p], out["net1"][p] = cs, dc, cps, loss, net
        out["npv"][p] = npv
    return out


def horizon_value(res, pack, econ: EconConfig, cell_level: bool) -> dict:
    """Per-block economics over a fixed service horizon (econ.horizon_years), the fair comparison when the two
    designs last different times. When a block retires (capacity limit or, in 'retire' mode, a hard fault), the
    owner installs a new block at that year's price (NREL mid-case decline) and ITC rate. Replacement block j of
    pack p behaves like simulated pack (p + j * 7919) mod P, so replacements are fresh, independent draws and both
    designs use the same mapping (paired). Fixed O&M (NLR ATB 2025: 4% of installed cost a year) is paid every year.
    The block in service at the end of the horizon is credited with straight-line salvage value. Arrays (P,)."""
    P, K = res.energy_kwh.shape
    spy = pack.steps_per_year
    H = int(round(econ.horizon_years * spy))
    life = np.where(np.isfinite(res.retirement_year), np.round(res.retirement_year * spy), K).astype(int)
    life = np.maximum(life, 1)
    vk = getattr(res, "visits_by_step", None)
    over = 1 + (econ.bms_overhead if cell_level else 0.0)
    disc = lambda m: (1 + econ.discount_rate) ** (-(m / spy))
    out = {k: np.zeros(P) for k in ("npv", "mwh_ac", "blocks", "capex_pv", "revenue_pv", "om_pv", "salvage_pv", "payback")}
    om_year = econ.fom_frac * econ.installed_cost * pack.nameplate_kwh
    for p in range(P):
        E = np.zeros(H); A = np.ones(H); V = np.zeros(H)
        capex = []                                   # (month, $ paid after ITC)
        m, j, salvage = 0, 0, 0.0
        while m < H:
            q = (p + j * 7919) % P
            L = int(life[q])
            year = econ.start_year + m / spy
            paid = econ.installed_cost * econ.cost_factor(year) * pack.nameplate_kwh * over * (1 - econ.itc_rate(int(year)))
            capex.append((m, paid))
            n = min(L, H - m)
            E[m:m + n] = res.energy_kwh[q, :n]
            A[m:m + n] = res.availability[q, :n]
            if vk is not None:
                V[m:m + n] = vk[q, :n]
            if m + L > H:                            # still in service at the horizon: straight-line salvage
                salvage = paid * (m + L - H) / L
            m += L; j += 1
        out["blocks"][p] = j
        npv = -sum(c * disc(mm) for mm, c in capex)
        cum, payback = -capex[0][1], np.inf
        rev_pv = om_pv = 0.0
        for y in range(econ.horizon_years):
            sl = slice(y * spy, (y + 1) * spy)
            e = E[sl].mean() * econ.ac_efficiency
            a = A[sl].mean()
            cs = econ.cs_rate * min(pack.rated_kw, e / econ.cs_event_hours) * a
            dc = 12 * econ.dc_rate * econ.dc_realization * min(pack.rated_kw, e / econ.dc_hours) * a
            cps = econ.cps_clear * econ.acp(econ.start_year + y) * econ.cps_multiplier * e / 1000 * max(pack.cycles_per_year - econ.cs_event_days, 0) * a
            mwh = e / 1000 * pack.cycles_per_year * a
            loss = mwh * (1 / econ.round_trip_efficiency - 1) * econ.energy_price * 1000
            visit = econ.visit_cost * V[sl].sum()
            net = cs + dc + cps - loss - visit - om_year
            d = (1 + econ.discount_rate) ** (y + 1)
            npv += net / d
            rev_pv += (cs + dc + cps) / d
            om_pv += om_year / d
            out["mwh_ac"][p] += mwh
            prev = cum
            cum += net - sum(c for mm, c in capex[1:] if y * spy <= mm < (y + 1) * spy)
            if not np.isfinite(payback) and cum >= 0:
                payback = y + (-prev / net if net > 0 else 0.0)
        sv = salvage * disc(H)
        out["npv"][p] = npv + sv
        out["capex_pv"][p] = sum(c * disc(mm) for mm, c in capex)
        out["revenue_pv"][p], out["om_pv"][p], out["salvage_pv"][p] = rev_pv, om_pv, sv
        out["payback"][p] = payback
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
    hf = horizon_value(results["fixed"], pack, econ, cell_level=False)
    hc = horizon_value(results["bypass"], pack, econ, cell_level=True)
    dh = (hc["npv"] - hf["npv"]) * n
    summary["horizon"] = {
        "years": econ.horizon_years,
        "fixed": {k: float(np.mean(v)) * (1 if k in ("payback", "blocks") else n) for k, v in hf.items() if k != "payback"},
        "bypass": {k: float(np.mean(v)) * (1 if k in ("payback", "blocks") else n) for k, v in hc.items() if k != "payback"},
        "payback_fixed": med(hf["payback"]), "payback_bypass": med(hc["payback"]),
        "npv_gain_mean": float(np.mean(dh)), "npv_gain_p10": float(np.percentile(dh, 10)),
        "npv_gain_p50": med(dh), "npv_gain_p90": float(np.percentile(dh, 90)),
        "blocks_fixed": float(np.mean(hf["blocks"])), "blocks_bypass": float(np.mean(hc["blocks"])),
    }
    summary["environment"] = {
        "life_fixed": life_f, "life_bypass": life_c,
        "co2_operation_t": summary["delta"]["mwh_ac"] * econ.grid_co2_lb_per_mwh / LB_PER_T,
        "avoided_cell_kwh": avoided_kwh,
        "co2_cells_t": avoided_kwh * econ.embodied_co2_kg_per_kwh / 1000,
        "cells_kg": avoided_kwh * econ.cell_kg_per_kwh,
    }
    return summary


__all__ = ["EconConfig", "pack_value", "horizon_value", "site_value"]
