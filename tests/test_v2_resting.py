"""Remaining-life and temperature-triggered resting (Methodology v2, Section 5)."""
import numpy as np

from reon_model.control import ControlPolicy, RemainingLifeTracker
from reon_model.simulate import HazardConfig, PackConfig, compare


def test_tracker_recovers_linear_fade():
    tr = RemainingLifeTracker((1, 3))
    rates = np.array([0.01, 0.02, 0.04])            # fade per year
    for m in range(13):
        tr.update((1.0 - rates * m / 12)[None, :])
    assert np.allclose(tr.own_rate()[0], rates, rtol=1e-6)
    cap = (1.0 - rates)[None, :]
    life = tr.life(cap, np.ones((1, 3), bool), 0.7)[0]
    assert life[2] < life[1] < life[0]               # fastest fader retires first


def test_tracker_needs_six_months():
    tr = RemainingLifeTracker((1, 2))
    for m in range(5):
        tr.update(np.array([[1.0 - 0.01 * m, 1.0]]))
    assert np.all(np.isnan(tr.own_rate()))


def test_rest_by_life_respects_headroom_and_stop():
    pol = ControlPolicy(rest_count=3, rest_by="remaining_life", rest_threshold=0.1, rest_stop_health=0.85)
    life = np.array([[1.0, 2.0, 9.0, 9.0, 9.0]]); act = np.ones((1, 5), bool)
    r = pol.rest_by_life(life, act, np.array([2]), np.array([0.9]))   # headroom 2, spare 1 -> one cell
    assert r.sum() == 1 and r[0, 0]
    r = pol.rest_by_life(life, act, np.array([4]), np.array([0.84]))  # pack below stop -> none
    assert r.sum() == 0


def test_rest_hot_picks_hottest():
    pol = ControlPolicy(rest_temp_C=1.0)
    temp = np.array([[0.0, 0.0, 3.0, 0.0]]); act = np.ones((1, 4), bool)
    assert pol.rest_hot(temp, act, np.array([3]))[0].tolist() == [False, False, True, False]


def test_defaults_unchanged_and_resting_runs():
    pack = PackConfig(years=10)
    base = compare(n_packs=8, pack=pack, hazard=HazardConfig.off())
    pol = ControlPolicy(rest_count=2, rest_by="remaining_life", rest_threshold=0.2, rest_stop_health=0.85)
    rest = compare(n_packs=8, pack=pack, hazard=HazardConfig.off(), policy=pol)
    assert np.array_equal(base["fixed"].energy_kwh, rest["fixed"].energy_kwh)     # fixed string untouched
    assert rest["bypass"].rested_cell_steps.sum() > 0
