"""Poisson and non-homogeneous Poisson process (NHPP) primitives.

Everything here is built on one object, the cumulative intensity

    Lambda(t) = integral_0^t lambda(s) ds,

and two facts about an NHPP with intensity lambda(t):

  1. N(t) ~ Poisson(Lambda(t)), and counts in disjoint windows are independent.
  2. (Time-rescaling) If 0 < E_1 < E_2 < ... are arrival times of a *unit-rate*
     homogeneous Poisson process, then t_j = Lambda^{-1}(E_j) are arrival times
     of the NHPP.

Reduction to the simple Poisson process
---------------------------------------
If lambda(t) = lambda for all t (every piece / every cell has the same rate),
then Lambda(t) = lambda * t, so

  * N(t) ~ Poisson(lambda * t)                         (fact 1)
  * Lambda^{-1}(s) = s / lambda, so t_j = E_j / lambda  (fact 2)
    -> inter-arrival times are i.i.d. Exponential(lambda).
  * The survival function of the first event is exp(-lambda * t).

Because every function below is written in terms of Lambda and Lambda^{-1},
the homogeneous case is not a separate code path: it falls out exactly,
and ``tests/test_nhpp.py`` checks it numerically.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import stats


# ---------------------------------------------------------------------------
# Piecewise-constant intensity (the workhorse: matches monthly BMS telemetry)
# ---------------------------------------------------------------------------
class PiecewiseConstantIntensity:
    """lambda(t) = rates[k] for t in [edges[k], edges[k+1]).

    After the last edge the last rate is assumed to continue, so the process
    is defined on [edges[0], inf). ``edges[0]`` must be 0.
    """

    def __init__(self, edges, rates):
        edges = np.asarray(edges, dtype=float)
        rates = np.asarray(rates, dtype=float)
        if edges.ndim != 1 or rates.ndim != 1 or len(edges) != len(rates) + 1:
            raise ValueError("need len(edges) == len(rates) + 1")
        if edges[0] != 0.0 or np.any(np.diff(edges) <= 0):
            raise ValueError("edges must start at 0 and be strictly increasing")
        if np.any(rates < 0):
            raise ValueError("rates must be non-negative")
        self.edges = edges
        self.rates = rates
        # cumulative intensity at each edge
        self._cum = np.concatenate([[0.0], np.cumsum(rates * np.diff(edges))])

    # -- constructors -------------------------------------------------------
    @classmethod
    def homogeneous(cls, rate: float, horizon: float = 1.0) -> "PiecewiseConstantIntensity":
        return cls([0.0, horizon], [rate])

    # -- queries ------------------------------------------------------------
    @property
    def is_homogeneous(self) -> bool:
        return bool(np.allclose(self.rates, self.rates[0]))

    def _bin(self, t):
        t = np.asarray(t, dtype=float)
        return np.clip(np.searchsorted(self.edges, t, side="right") - 1, 0, len(self.rates) - 1)

    def intensity(self, t):
        return self.rates[self._bin(t)]

    def cumulative(self, t):
        """Lambda(t)."""
        t = np.asarray(t, dtype=float)
        k = self._bin(t)
        return self._cum[k] + self.rates[k] * (t - self.edges[k])

    def inverse_cumulative(self, s):
        """Lambda^{-1}(s): the earliest t with Lambda(t) = s (inf if never reached)."""
        s = np.atleast_1d(np.asarray(s, dtype=float))
        out = np.full(s.shape, np.inf)
        # Only bins with positive rate can contain the solution.
        pos = np.flatnonzero(self.rates > 0)
        if pos.size == 0:
            return out if out.size > 1 else out[0]
        starts = self._cum[pos]
        j = np.searchsorted(starts, s, side="right") - 1
        ok = j >= 0
        k = pos[np.clip(j, 0, None)]
        t = self.edges[k] + (s - self._cum[k]) / self.rates[k]
        # A solution inside bin k must not run past that bin's end
        # (except the last bin, which extends to infinity).
        last = len(self.rates) - 1
        within = (k == last) | (t <= self.edges[np.minimum(k + 1, last + 1)])
        out[ok & within] = t[ok & within]
        # s == 0 maps to 0
        out[s == 0] = 0.0
        return out if out.size > 1 else out[0]

    def count_pmf(self, n, t):
        """P(N(t) = n) = Poisson pmf with mean Lambda(t)."""
        return stats.poisson.pmf(n, self.cumulative(t))

    def survival(self, t):
        """P(no event in [0, t]) = exp(-Lambda(t)). Also the cell's reliability."""
        return np.exp(-self.cumulative(t))

    def sample(self, horizon: float, rng: np.random.Generator) -> np.ndarray:
        """Event times on [0, horizon] by time-rescaling a unit-rate process."""
        total = float(self.cumulative(horizon))
        unit_arrivals = []
        s = rng.exponential(1.0)
        while s <= total:
            unit_arrivals.append(s)
            s += rng.exponential(1.0)
        if not unit_arrivals:
            return np.empty(0)
        return np.atleast_1d(self.inverse_cumulative(np.array(unit_arrivals)))


def superpose(intensities: list[PiecewiseConstantIntensity]) -> PiecewiseConstantIntensity:
    """Superposition of independent NHPPs is an NHPP with summed intensity.

    For N cells sharing rate lambda this is a homogeneous process with rate N*lambda.
    """
    edges = np.unique(np.concatenate([p.edges for p in intensities]))
    mids = 0.5 * (edges[:-1] + edges[1:])
    rates = np.sum([p.intensity(mids) for p in intensities], axis=0)
    return PiecewiseConstantIntensity(edges, rates)


# ---------------------------------------------------------------------------
# Parametric NHPP families used in reliability engineering
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class PowerLawIntensity:
    """Crow-AMSAA: Lambda(t) = lam * t**beta,  lambda(t) = lam*beta*t**(beta-1).

    beta > 1: wear-out (rate rises with age); beta < 1: infant mortality;
    beta == 1: homogeneous Poisson with rate lam.
    """

    lam: float
    beta: float

    def cumulative(self, t):
        return self.lam * np.asarray(t, dtype=float) ** self.beta

    def intensity(self, t):
        t = np.asarray(t, dtype=float)
        return self.lam * self.beta * t ** (self.beta - 1.0)

    def inverse_cumulative(self, s):
        return (np.asarray(s, dtype=float) / self.lam) ** (1.0 / self.beta)

    @staticmethod
    def fit(event_times, horizon: float) -> "PowerLawIntensity":
        """Time-truncated MLE for a single system observed on [0, horizon]."""
        t = np.asarray(event_times, dtype=float)
        n = t.size
        if n == 0:
            raise ValueError("need at least one event")
        beta = n / np.sum(np.log(horizon / t))
        return PowerLawIntensity(lam=n / horizon**beta, beta=beta)


@dataclass(frozen=True)
class LogLinearIntensity:
    """lambda(t) = exp(alpha + beta*t).  beta == 0 reduces to rate exp(alpha)."""

    alpha: float
    beta: float

    def intensity(self, t):
        return np.exp(self.alpha + self.beta * np.asarray(t, dtype=float))

    def cumulative(self, t):
        t = np.asarray(t, dtype=float)
        if self.beta == 0.0:
            return np.exp(self.alpha) * t
        # expm1 keeps this accurate as beta -> 0 (limit is exp(alpha) * t)
        return np.exp(self.alpha) * np.expm1(self.beta * t) / self.beta


# ---------------------------------------------------------------------------
# Counting failed cells in a pack
# ---------------------------------------------------------------------------
def poisson_binomial_pmf(p) -> np.ndarray:
    """pmf of the number of successes among independent Bernoulli(p_i).

    Used for "how many cells have faulted by time t", with p_i = 1 - exp(-Lambda_i(t)).
    If all p_i are equal this is exactly Binomial(N, p).
    """
    p = np.asarray(p, dtype=float)
    pmf = np.zeros(p.size + 1)
    pmf[0] = 1.0
    for pi in p:
        pmf[1:] = pmf[1:] * (1.0 - pi) + pmf[:-1] * pi
        pmf[0] *= 1.0 - pi
    return pmf


def fixed_string_survival(cell_cumulative_hazards) -> np.ndarray:
    """P(no cell faults) for a fixed series string = exp(-sum_i Lambda_i).

    That is the survival of the superposed NHPP; equal rates give exp(-N*lambda*t).
    Accepts shape (n_cells,) or (n_cells, n_times).
    """
    return np.exp(-np.sum(np.asarray(cell_cumulative_hazards, dtype=float), axis=0))


def bypass_survival(cell_cumulative_hazards, k: int) -> np.ndarray:
    """P(at most k cells have faulted): a pack that can bypass k cells stays up.

    k = 0 recovers ``fixed_string_survival`` exactly.
    """
    L = np.asarray(cell_cumulative_hazards, dtype=float)
    if L.ndim == 1:
        return float(np.sum(poisson_binomial_pmf(-np.expm1(-L))[: k + 1]))
    return np.array([np.sum(poisson_binomial_pmf(-np.expm1(-L[:, j]))[: k + 1]) for j in range(L.shape[1])])
