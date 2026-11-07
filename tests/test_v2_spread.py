"""Chemistry-agnostic spread multiplier and early-knee outliers (Methodology v2, Section 3)."""
import numpy as np

from reon_model.simulate import AgingConfig, draw_cell_parameters


def _draw(**kw):
    return draw_cell_parameters(AgingConfig(**kw), 20000, np.random.default_rng(7))


def test_defaults_reproduce_calibrated_draws():
    a = draw_cell_parameters(AgingConfig(), 50, np.random.default_rng(3))
    b = draw_cell_parameters(AgingConfig(spread_multiplier=1.0, outlier_fraction=0.0), 50, np.random.default_rng(3))
    for key in ("m", "tau_rel", "kappa", "q0", "r0", "temp"):
        assert np.array_equal(a[key], b[key])


def test_spread_multiplier_scales_rate_spread():
    s1, s2 = _draw()["m"].std(), _draw(spread_multiplier=2.0)["m"].std()
    assert 1.8 < s2 / s1 < 2.2


def test_narrow_spread_stays_valid():
    d = _draw(spread_multiplier=0.25)
    assert np.all(np.isfinite(d["m"])) and d["m"].std() > 0


def test_outliers_knee_early():
    base, out = _draw(), _draw(outlier_fraction=0.2, outlier_knee_factor=0.8)
    assert out["tau_rel"].mean() < base["tau_rel"].mean() * 0.98
