"""Massachusetts C&I economics and environment (Methodology v2, Sections 7-9)."""
from types import SimpleNamespace

import numpy as np
import pytest

from reon_model.economics import EconConfig, pack_value, site_value
from reon_model.simulate import PackConfig


def _res(energy, life_years, K=24):
    return SimpleNamespace(energy_kwh=np.full((1, K), energy), availability=np.ones((1, K)),
                           retirement_year=np.array([life_years]))


def test_one_year_hand_calculation():
    pack, e = PackConfig(), EconConfig()
    v = pack_value(_res(60.0, 1.0), pack, e, cell_level=False)
    E = 60.0 * e.ac_efficiency
    cs = 200 * min(30, E / 3)
    dc = 12 * 33.95 * e.dc_realization * min(30, E / 2)
    cps = 0.87 * 65 * E / 1000 * (365 - 45)
    loss = E / 1000 * 365 * (1 / 0.88 - 1) * 0.20 * 1000
    capex = 600 * pack.nameplate_kwh * 0.7
    assert v["net1"][0] == pytest.approx(cs + dc + cps - loss)
    assert v["npv"][0] == pytest.approx(-capex + (cs + dc + cps - loss) / 1.08)
    assert v["capex"][0] == pytest.approx(capex)


def test_overhead_raises_capex():
    pack, e = PackConfig(), EconConfig(bms_overhead=0.05)
    f = pack_value(_res(60.0, 1.0), pack, e, cell_level=False)["capex"][0]
    c = pack_value(_res(60.0, 1.0), pack, e, cell_level=True)["capex"][0]
    assert c / f == pytest.approx(1.05)


def test_acp_drops_after_2032():
    e = EconConfig()
    assert e.acp(2032) == 65 and e.acp(2033) == 45


def test_longer_life_gives_value_and_environment():
    pack, e = PackConfig(), EconConfig()
    s = site_value({"fixed": _res(60.0, 1.0), "bypass": _res(60.0, 2.0)}, pack, e)
    assert s["delta"]["npv_p50"] > 0 and s["delta"]["mwh_ac"] > 0
    env = s["environment"]
    assert env["avoided_cell_kwh"] > 0 and env["co2_cells_t"] > 0 and env["cells_kg"] > 0
