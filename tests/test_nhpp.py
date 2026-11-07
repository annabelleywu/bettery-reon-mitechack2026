"""The NHPP must reduce to a simple Poisson process when all the lambdas are equal."""

import numpy as np
import pytest
from scipy import stats

from reon_model.nhpp import (
    LogLinearIntensity,
    PiecewiseConstantIntensity,
    PowerLawIntensity,
    bypass_survival,
    fixed_string_survival,
    poisson_binomial_pmf,
    superpose,
)

LAM = 0.7
EDGES = np.array([0.0, 0.5, 1.3, 2.0, 4.0])
T = np.linspace(0.0, 6.0, 61)


def equal_rate_process():
    return PiecewiseConstantIntensity(EDGES, np.full(len(EDGES) - 1, LAM))


def test_equal_pieces_cumulative_is_lambda_t():
    p = equal_rate_process()
    assert p.is_homogeneous
    np.testing.assert_allclose(p.cumulative(T), LAM * T, rtol=1e-12, atol=1e-12)
    np.testing.assert_allclose(p.intensity(T), LAM)


def test_equal_pieces_inverse_is_s_over_lambda():
    s = np.linspace(0.0, 5.0, 51)
    np.testing.assert_allclose(equal_rate_process().inverse_cumulative(s), s / LAM, rtol=1e-12)


def test_equal_pieces_count_distribution_is_poisson_lambda_t():
    p = equal_rate_process()
    for t in (0.3, 1.0, 3.7):
        n = np.arange(15)
        np.testing.assert_allclose(p.count_pmf(n, t), stats.poisson.pmf(n, LAM * t), rtol=1e-12)
        assert p.survival(t) == pytest.approx(np.exp(-LAM * t))


def test_equal_pieces_samples_match_homogeneous_draw_for_draw():
    """Same random numbers -> identical event times (time-rescaling, Lambda^-1(s) = s/lambda)."""
    a = equal_rate_process().sample(50.0, np.random.default_rng(1))
    b = PiecewiseConstantIntensity.homogeneous(LAM, 50.0).sample(50.0, np.random.default_rng(1))
    np.testing.assert_allclose(a, b, rtol=1e-12)


def test_equal_pieces_interarrivals_are_exponential():
    times = equal_rate_process().sample(20000.0, np.random.default_rng(2))
    gaps = np.diff(np.concatenate([[0.0], times]))
    assert stats.kstest(gaps, "expon", args=(0, 1 / LAM)).pvalue > 0.01


def test_unequal_pieces_counts_are_poisson_with_integrated_rate():
    p = PiecewiseConstantIntensity([0, 1, 2, 3], [0.2, 2.0, 0.5])
    rng = np.random.default_rng(3)
    counts = np.array([p.sample(3.0, rng).size for _ in range(20000)])
    assert p.cumulative(3.0) == pytest.approx(2.7)
    assert counts.mean() == pytest.approx(2.7, rel=0.03)
    assert counts.var() == pytest.approx(2.7, rel=0.06)  # Poisson: var == mean


def test_zero_rate_piece_handled():
    p = PiecewiseConstantIntensity([0, 1, 2, 3], [1.0, 0.0, 1.0])
    assert p.inverse_cumulative(1.5) == pytest.approx(2.5)
    assert p.cumulative(1.7) == pytest.approx(1.0)


def test_superposition_of_equal_cells_is_poisson_n_lambda():
    n_cells = 96
    cells = [equal_rate_process() for _ in range(n_cells)]
    pack = superpose(cells)
    assert pack.is_homogeneous
    np.testing.assert_allclose(pack.cumulative(T), n_cells * LAM * T, rtol=1e-12)


def test_superposition_of_unequal_cells_sums_intensities():
    a = PiecewiseConstantIntensity([0, 1, 3], [1.0, 2.0])
    b = PiecewiseConstantIntensity([0, 2, 3], [0.5, 4.0])
    s = superpose([a, b])
    np.testing.assert_allclose(s.cumulative(T), a.cumulative(T) + b.cumulative(T), rtol=1e-12)


def test_power_law_beta_one_is_homogeneous():
    pl = PowerLawIntensity(lam=LAM, beta=1.0)
    np.testing.assert_allclose(pl.cumulative(T), LAM * T)
    np.testing.assert_allclose(pl.intensity(T[1:]), LAM)


def test_power_law_mle_recovers_beta_near_one_for_poisson_data():
    times = PiecewiseConstantIntensity.homogeneous(2.0, 1.0).sample(2000.0, np.random.default_rng(4))
    fit = PowerLawIntensity.fit(times, 2000.0)
    assert fit.beta == pytest.approx(1.0, abs=0.05)


def test_log_linear_beta_zero_is_homogeneous_and_continuous():
    ll0 = LogLinearIntensity(alpha=np.log(LAM), beta=0.0)
    np.testing.assert_allclose(ll0.cumulative(T), LAM * T)
    llsmall = LogLinearIntensity(alpha=np.log(LAM), beta=1e-10)
    np.testing.assert_allclose(llsmall.cumulative(T), LAM * T, rtol=1e-8)


def test_poisson_binomial_with_equal_p_is_binomial():
    p = 0.13
    np.testing.assert_allclose(poisson_binomial_pmf(np.full(40, p)), stats.binom.pmf(np.arange(41), 40, p), atol=1e-14)


def test_fixed_string_survival_equal_rates():
    n, t = 96, 2.5
    L = np.full(n, LAM * t)
    assert fixed_string_survival(L) == pytest.approx(np.exp(-n * LAM * t))
    # bypass with k = 0 is the fixed string
    assert bypass_survival(L, 0) == pytest.approx(fixed_string_survival(L))


def test_bypass_survival_equal_rates_is_binomial_cdf():
    n, k = 96, 4
    L = np.full(n, 0.03)
    p = 1 - np.exp(-0.03)
    assert bypass_survival(L, k) == pytest.approx(stats.binom.cdf(k, n, p))
    assert bypass_survival(L, k) > fixed_string_survival(L)
