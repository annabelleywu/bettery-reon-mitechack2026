import numpy as np
import pytest
from scipy import stats

from reon_model import (
    FEATURES,
    HazardConfig,
    PackConfig,
    PoissonIntensityGLM,
    simulate,
    usable_capacity,
)


# --------------------------------------------------------------------------- GLM
def synthetic_rows(beta, base=0.05, n=200_000, seed=0):
    rng = np.random.default_rng(seed)
    X = rng.standard_normal((n, len(beta)))
    e = rng.uniform(0.2, 1.0, n)
    y = rng.poisson(e * base * np.exp(X @ np.asarray(beta)))
    return X, y, e


def test_intercept_only_fit_is_exact_poisson_mle():
    X, y, e = synthetic_rows([0.0, 0.0])
    m = PoissonIntensityGLM().fit(np.empty((len(y), 0)), y, e)
    assert np.exp(m.intercept_) == pytest.approx(y.sum() / e.sum(), rel=1e-12)


def test_constant_features_collapse_to_homogeneous_rate():
    """All cells look identical -> all lambdas equal -> simple Poisson MLE."""
    _, y, e = synthetic_rows([0.0])
    X = np.full((len(y), 3), 1.7)
    m = PoissonIntensityGLM().fit(X, y, e)
    np.testing.assert_array_equal(m.coef_, 0.0)
    assert m.predict_rate(X[:5]) == pytest.approx(np.full(5, y.sum() / e.sum()), rel=1e-10)


def test_homogeneous_data_lrt_does_not_reject():
    X, y, e = synthetic_rows([0.0, 0.0, 0.0], seed=1)
    m = PoissonIntensityGLM().fit(X, y, e)
    res = m.lrt_vs_homogeneous()
    assert res["p_value"] > 0.01
    assert np.all(np.abs(m.coef_) < 4 * m.se_[1:])
    assert np.exp(m.intercept_) == pytest.approx(0.05, rel=0.05)


def test_heterogeneous_data_recovers_coefficients_and_rejects_h0():
    beta = np.array([0.4, -0.25, 0.0])
    X, y, e = synthetic_rows(beta, seed=2)
    m = PoissonIntensityGLM().fit(X, y, e)
    assert np.all(np.abs(m.coef_ - beta) < 4 * m.se_[1:])
    assert m.lrt_vs_homogeneous()["p_value"] < 1e-6


# --------------------------------------------------------------- usable capacity
def test_usable_capacity_limits():
    rng = np.random.default_rng(0)
    Q = rng.uniform(0.6, 1.0, (5, 16))
    act = np.ones_like(Q, dtype=bool)
    np.testing.assert_allclose(usable_capacity(Q, act, np.zeros(5, int)), 16 * Q.min(axis=1))
    np.testing.assert_allclose(usable_capacity(Q, act, np.full(5, 15)), Q.sum(axis=1))


def test_brief_sixteen_cell_example():
    Q = np.array([[0.85] * 15 + [0.70]])
    act = np.ones_like(Q, dtype=bool)
    assert usable_capacity(Q, act, np.array([0]))[0] == pytest.approx(16 * 0.70)
    assert usable_capacity(Q, act, np.array([1]))[0] == pytest.approx(15 * 0.85 + 0.70)


# ----------------------------------------------------------------- end to end
def test_fixed_string_with_equal_rates_gives_poisson_fault_counts():
    """beta = 0 and swap-on-fault: each slot is a renewal process with Exp(lambda)
    gaps, i.e. a Poisson process, so pack faults ~ Poisson(N * lambda * T)."""
    lam, years = 0.01, 10.0
    pack = PackConfig(years=years)
    res = simulate("fixed", n_packs=3000, pack=pack, hazard=HazardConfig.homogeneous(lam), seed=5)
    expected = pack.n_series * lam * years
    assert res.faults.mean() == pytest.approx(expected, rel=0.03)
    assert res.faults.var() / res.faults.mean() == pytest.approx(1.0, abs=0.08)  # dispersion
    counts = np.bincount(res.faults.astype(int), minlength=30)[:30]
    chi = stats.chisquare(counts[2:18], stats.poisson.pmf(np.arange(2, 18), expected)
                          * counts[2:18].sum() / stats.poisson.pmf(np.arange(2, 18), expected).sum())
    assert chi.pvalue > 0.001


def test_simulation_rows_refit_true_hazard():
    hz = HazardConfig(base_rate=0.004)
    res = simulate("bypass", n_packs=150, hazard=hz, seed=7, record_rows=True)
    r = res.rows
    m = PoissonIntensityGLM(feature_names=FEATURES).fit(r["X"], r["events"], r["exposure"])
    assert np.all(np.abs(m.coef_ - hz.beta) < 4 * m.se_[1:] + 1e-9)


def test_bypass_never_worse_than_fixed_before_first_fault():
    res_f = simulate("fixed", n_packs=50, seed=3, hazard=HazardConfig(base_rate=1e-9))
    res_b = simulate("bypass", n_packs=50, seed=3, hazard=HazardConfig(base_rate=1e-9),
                     pack=PackConfig(switch_efficiency=1.0))
    assert np.all(res_b.energy_kwh >= res_f.energy_kwh - 1e-9)
