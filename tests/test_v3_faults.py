"""Hard cell faults: how a conventional string and cell-level control live with them (v3)."""
import dataclasses

import numpy as np

from reon_model.economics import EconConfig, pack_value
from reon_model.simulate import AgingConfig, HazardConfig, PackConfig, compare

PACK = PackConfig(n_series=40, bypass_headroom=4, years=10)
HIGH = HazardConfig.homogeneous(0.01)   # 1% per cell-year: many faults, so the test is quick


def test_retire_mode_ends_fixed_string_at_first_fault():
    pk = dataclasses.replace(PACK, on_string_fault="retire")
    r = compare(n_packs=60, pack=pk, aging=AgingConfig(), hazard=HIGH, seed=3)
    f, b = r["fixed"], r["bypass"]
    assert f.retired_by_fault.mean() > 0.5            # 40 cells x 1%/y: most strings see a fault within 10 y
    assert b.retired_by_fault.mean() < f.retired_by_fault.mean()
    assert np.mean(b.delivered_mwh) > np.mean(f.delivered_mwh)
    assert f.service_visits.sum() == 0                # retired, not repaired


def test_repair_mode_counts_visits_by_step():
    r = compare(n_packs=40, pack=PACK, aging=AgingConfig(), hazard=HIGH, seed=4)
    for res in r.values():
        assert np.allclose(res.visits_by_step.sum(axis=1), res.service_visits)
    assert r["bypass"].service_visits.sum() < r["fixed"].service_visits.sum()


def test_no_faults_unchanged_by_mode():
    a = compare(n_packs=20, pack=PACK, hazard=HazardConfig.off(), seed=5)
    b = compare(n_packs=20, pack=dataclasses.replace(PACK, on_string_fault="retire"), hazard=HazardConfig.off(), seed=5)
    for m in ("fixed", "bypass"):
        assert np.allclose(a[m].delivered_mwh, b[m].delivered_mwh)


def test_visit_cost_lowers_npv():
    r = compare(n_packs=20, pack=PACK, aging=AgingConfig(), hazard=HIGH, seed=6)
    cheap = pack_value(r["fixed"], PACK, EconConfig(visit_cost=0.0), cell_level=False)
    dear = pack_value(r["fixed"], PACK, EconConfig(visit_cost=1500.0), cell_level=False)
    assert np.all(dear["npv"] <= cheap["npv"] + 1e-9)
    assert dear["visit_cost"].sum() > 0


def test_horizon_value_hand_calculation():
    """One pack, constant 60 kWh for 10 years then retired: two blocks over 20 years, checked by hand."""
    from types import SimpleNamespace
    from reon_model.economics import horizon_value
    pk = PackConfig(years=20, n_series=250, cell_ah=60000 / (250 * 3.1), bypass_headroom=25)
    K = 240
    res = SimpleNamespace(energy_kwh=np.full((1, K), 60.0), availability=np.ones((1, K)),
                          retirement_year=np.array([10.0]), visits_by_step=np.zeros((1, K)))
    ec = EconConfig(start_year=2027)
    v = horizon_value(res, pk, ec, cell_level=False)
    assert v["blocks"][0] == 2
    # capex: block 1 in 2027 at 30% ITC; block 2 in 2037 at that year's cost factor and no ITC
    c1 = 600 * 60 * 0.7
    c2 = 600 * ec.cost_factor(2037) * 60 * 1.0 / 1.08 ** 10
    assert np.isclose(v["capex_pv"][0], c1 + c2)
    # yearly cash flow is the same every year; no salvage (second block ends exactly at the horizon)
    e = 60 * 0.96
    yearly = (200 * min(30, e / 3) + 12 * 33.95 * ec.dc_realization * min(30, e / 2)
              - e / 1000 * 365 * (1 / 0.88 - 1) * 200 - ec.fom_frac * 600 * 60)
    cps = sum(0.87 * ec.acp(2027 + y) * e / 1000 * (365 - 45) / 1.08 ** (y + 1) for y in range(20))
    annuity = sum(1 / 1.08 ** (y + 1) for y in range(20))
    assert np.isclose(v["npv"][0], yearly * annuity + cps - (c1 + c2), rtol=1e-9)
    assert v["salvage_pv"][0] == 0
