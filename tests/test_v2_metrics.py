"""kW metrics, beta_power, beta_SOH and the retention denominator (Methodology v2, Section 6)."""
import numpy as np

from reon_model.simulate import HazardConfig, PackConfig, beta_power, compare


def test_beta_power_equal_cells_is_one():
    R = np.ones((2, 5)); act = np.ones((2, 5), bool)
    assert np.allclose(beta_power(R, act, np.array([0, 2]), 3.0, 2.5), 1.0)


def test_beta_power_bypass_never_worse_and_drops_high_resistance():
    R = np.array([[1.0, 1.0, 1.0, 3.0]]); act = np.ones((1, 4), bool)
    fixed = beta_power(R, act, np.array([0]), 3.0, 2.5)[0]
    byp = beta_power(R, act, np.array([1]), 3.0, 2.5)[0]
    assert fixed < byp <= 1.0


def test_beta_power_scale_free():
    rng = np.random.default_rng(0); R = 1 + 0.1 * rng.random((3, 10)); act = np.ones((3, 10), bool)
    h = np.array([0, 1, 2])
    assert np.allclose(beta_power(R, act, h, 3.0, 2.5), beta_power(R * 7.3, act, h, 3.0, 2.5))


def test_metrics_shapes_and_firm_kw():
    pack = PackConfig(years=6)
    r = compare(n_packs=6, pack=pack, hazard=HazardConfig.off())
    for m in r.values():
        assert m.firm_kw.shape == m.energy_kwh.shape == m.beta_power.shape == m.beta_soh.shape
        assert np.all(m.firm_kw <= pack.rated_kw + 1e-9)
        assert np.allclose(m.firm_kw[:, 0], np.minimum(pack.rated_kw, m.energy_kwh[:, 0] / pack.event_hours))
        assert np.all((m.beta_soh[:, 0] > 0.95) & (m.beta_soh[:, 0] <= 1.0))
    assert np.nanmedian(r["fixed"].beta_power[:, 0]) > 0.8


def test_retention_bol_starts_at_one():
    r = compare(n_packs=4, pack=PackConfig(years=3, retention_basis="bol"), hazard=HazardConfig.off())
    for m in r.values():
        assert np.allclose(m.retention[:, 0], 1.0)
