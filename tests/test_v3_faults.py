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
