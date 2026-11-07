"""Adjustable monitoring signals and bypass policy (the brief's two given capabilities)."""

import numpy as np
import pytest

from reon_model import (
    AgingConfig, ControlPolicy, HazardConfig, MonitoringConfig, PackConfig, PoissonIntensityGLM,
    SIGNALS, simulate,
)
from reon_model.monitoring import Monitor
from reon_model.simulate import _CellSlots

NO_FAULTS = HazardConfig(base_rate=1e-12)


# ------------------------------------------------------------------ monitoring
def test_all_brief_signals_are_adjustable():
    assert set(SIGNALS) == {"voltage", "temperature", "soc", "soh", "capacity", "resistance", "ocv", "history"}
    m = MonitoringConfig()
    for s in SIGNALS:
        spec = getattr(m, s)
        assert spec.enabled and spec.noise >= 0


def test_disabling_signals_removes_their_features():
    full = MonitoringConfig().feature_names()
    assert len(full) == 7
    conv = MonitoringConfig.only("voltage", "temperature").feature_names()
    assert conv == ["temp_offset_C", "eod_voltage_gap"]
    assert MonitoringConfig.only().feature_names() == []
    with pytest.raises(ValueError):
        MonitoringConfig.only("impedance_spectrum")


def test_measurement_noise_has_the_configured_size():
    cfg = MonitoringConfig.perfect()
    cfg.temperature.noise = 0.7
    mon = Monitor(cfg, 12, np.random.default_rng(0))
    shape = (200, 500)
    Q, q0, R, temp = np.full(shape, 0.9), np.ones(shape), np.ones(shape), np.zeros(shape)
    r = mon.read(Q, q0, R, temp, passed=np.full(shape, 0.8))
    assert r["temperature"].std() == pytest.approx(0.7, rel=0.02)
    np.testing.assert_allclose(r["soh"], 0.9)                     # noise-free
    np.testing.assert_allclose(r["soc"], 1 - 0.8 / 0.9)          # charge left at end of discharge


def test_weak_cell_shows_lowest_voltage_at_end_of_discharge():
    mon = Monitor(MonitoringConfig.perfect(), 12, np.random.default_rng(0))
    Q = np.array([[0.70] + [0.85] * 15])
    passed = np.full_like(Q, 0.70)                                 # fixed string stops at the weakest
    r = mon.read(Q, np.ones_like(Q), np.ones_like(Q), np.zeros_like(Q), passed)
    assert np.argmin(r["voltage"][0]) == 0 and np.argmin(r["ocv"][0]) == 0


# --------------------------------------------------------------------- aging
def test_throughput_aging_reduces_to_closed_form_at_full_use():
    ag_tp, ag_cf = AgingConfig(throughput_aging=True), AgingConfig(throughput_aging=False)
    a = _CellSlots(3, 20, ag_tp, 365.0, np.random.default_rng(1))
    b = _CellSlots(3, 20, ag_cf, 365.0, np.random.default_rng(1))
    for step in range(120):
        a.advance(1 / 12, np.ones((3, 20)))                         # full nameplate cycle every day
        b.advance(1 / 12, np.zeros((3, 20)))                        # ignored: closed form
    np.testing.assert_allclose(a.capacity(10.0), b.capacity(10.0), rtol=1e-12)


def test_idle_cell_ages_on_calendar_only():
    s = _CellSlots(1, 2, AgingConfig(), 365.0, np.random.default_rng(2))
    for _ in range(60):
        s.advance(1 / 12, np.array([[1.0, 0.0]]))
    assert s.efc[0, 1] == 0.0 and s.efc[0, 0] == pytest.approx(365 * 5)
    assert s.clock[0, 1] < s.clock[0, 0]


# --------------------------------------------------------------------- policy
def test_conventional_policy_on_bypass_hardware_equals_fixed_string():
    pack = PackConfig(years=8.0, switch_efficiency=1.0)
    f = simulate("fixed", n_packs=40, pack=pack, seed=4)
    b = simulate("bypass", n_packs=40, pack=pack, seed=4, policy=ControlPolicy.conventional())
    np.testing.assert_allclose(b.energy_kwh, f.energy_kwh)
    np.testing.assert_array_equal(b.service_visits, f.service_visits)


def test_isolation_respects_headroom_and_spare():
    pack = PackConfig(years=10.0, bypass_headroom=4)
    pol = ControlPolicy(isolate_if={"soh_gap": 0.005}, spare_for_faults=1)   # aggressive threshold
    r = simulate("bypass", n_packs=30, pack=pack, seed=5, hazard=NO_FAULTS, policy=pol)
    assert r.isolated.max() <= 3                                    # k - spare, no faults to free slots
    assert r.isolated.sum() > 0


def test_isolation_by_learned_risk_runs_end_to_end():
    mon = MonitoringConfig()
    train = simulate("bypass", n_packs=60, seed=6, record_rows=True, monitoring=mon,
                     hazard=HazardConfig(base_rate=0.004))
    glm = PoissonIntensityGLM(feature_names=train.rows["feature_names"]).fit(
        train.rows["X"], train.rows["events"], train.rows["exposure"])
    pol = ControlPolicy(isolate_if={"predicted_fault_rate": 0.02}, risk_model=glm)
    r = simulate("bypass", n_packs=30, seed=8, monitoring=mon, policy=pol)
    assert np.isfinite(r.delivered_mwh).all()


def test_rule_on_unmeasured_signal_is_refused():
    pol = ControlPolicy(isolate_if={"resistance_gap": 0.3})
    with pytest.raises(ValueError, match="not measured"):
        simulate("bypass", n_packs=5, seed=0, policy=pol,
                 monitoring=MonitoringConfig.only("voltage", "temperature"))


def test_resting_reduces_rested_cells_throughput():
    pack = PackConfig(years=3.0)
    base = simulate("bypass", n_packs=20, pack=pack, seed=9, hazard=NO_FAULTS)
    rest = simulate("bypass", n_packs=20, pack=pack, seed=9, hazard=NO_FAULTS,
                    policy=ControlPolicy(rest_count=2, rest_by="soh_gap"))
    assert rest.rested_cell_steps.min() > 0
    # resting gives up capacity in the steps it happens
    assert rest.energy_kwh[:, 12:].mean() < base.energy_kwh[:, 12:].mean()
