"""Learning per-cell fault intensities from BMS telemetry.

Model (a proportional-intensity NHPP, a.k.a. piecewise-exponential model):

    lambda_i(t) = lambda_0 * exp( beta . x_i(t) )

x_i(t) are features REON's per-cell monitoring can see (temperature offset,
state-of-health gap to the pack, resistance gap, ...), held constant within
each telemetry period. Data come as "cell-period" rows:

    (features x, exposure e = time at risk in the period, events y)

Within a period the cell is a homogeneous Poisson process with rate
lambda_0 * exp(beta . x), so the log-likelihood is the Poisson-GLM one:

    l(beta) = sum_r  y_r * log(e_r * lambda_r) - e_r * lambda_r   (+ const)

This is exact for right-censored first-fault times too (the classic
piecewise-exponential = Poisson-regression equivalence), so a cell that is
bypassed or replaced simply stops contributing rows.

Reduction to the simple Poisson process
---------------------------------------
* With no features, or beta = 0, every row has the same rate and the MLE
  is closed-form:  lambda_hat = sum(y) / sum(e)   (the textbook Poisson MLE).
  ``fit`` returns exactly that number in the intercept-only case.
* ``lrt_vs_homogeneous`` tests H0: all lambdas equal (beta = 0) against the
  NHPP with a likelihood-ratio chi-square test, so the data tell you
  whether the extra structure is needed.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from scipy import stats
from scipy.special import gammaln


def poisson_loglik(y, mu) -> float:
    y = np.asarray(y, dtype=float)
    mu = np.asarray(mu, dtype=float)
    with np.errstate(divide="ignore", invalid="ignore"):
        term = np.where(y > 0, y * np.log(mu), 0.0)
    return float(np.sum(term - mu - gammaln(y + 1.0)))


def poisson_deviance(y, mu) -> float:
    """Mean Poisson deviance (lower is better); a scoring rule for held-out data."""
    y = np.asarray(y, dtype=float)
    mu = np.asarray(mu, dtype=float)
    with np.errstate(divide="ignore", invalid="ignore"):
        term = np.where(y > 0, y * np.log(y / mu), 0.0)
    return float(2.0 * np.mean(term - (y - mu)))


@dataclass
class PoissonIntensityGLM:
    """Log-linear Poisson intensity model fitted by Newton-Raphson.

    ``l2`` is an optional ridge penalty on the (standardized) slopes; the
    intercept is never penalized, so the intercept-only MLE stays exact.
    """

    l2: float = 0.0
    max_iter: int = 100
    tol: float = 1e-10
    feature_names: list[str] | None = None

    # fitted attributes
    coef_: np.ndarray = field(default=None, init=False)          # slopes, raw feature units
    intercept_: float = field(default=None, init=False)          # log lambda_0 at x = 0
    se_: np.ndarray = field(default=None, init=False)            # SEs of [intercept, slopes]
    loglik_: float = field(default=None, init=False)
    n_events_: float = field(default=None, init=False)
    exposure_: float = field(default=None, init=False)

    # -- fitting -------------------------------------------------------------
    def fit(self, X, events, exposure) -> "PoissonIntensityGLM":
        X = np.asarray(X, dtype=float)
        if X.ndim == 1:
            X = X[:, None]
        y = np.asarray(events, dtype=float)
        e = np.asarray(exposure, dtype=float)
        keep = e > 0
        X, y, e = X[keep], y[keep], e[keep]
        n, p = X.shape
        self.n_events_, self.exposure_ = y.sum(), e.sum()
        if self.n_events_ == 0:
            raise ValueError("no events: the rate MLE is 0 and slopes are unidentifiable")

        # Standardize; zero-variance columns are dropped (they are collinear
        # with the intercept: "all cells look the same" -> homogeneous rate).
        self._mean = X.mean(axis=0) if p else np.zeros(0)
        sd = X.std(axis=0) if p else np.zeros(0)
        scale = np.maximum(np.abs(X).max(axis=0), 1.0) if p else np.zeros(0)
        self._active = (X.max(axis=0) > X.min(axis=0)) & (sd > 1e-9 * scale) if p else np.zeros(0, bool)
        self._sd = np.where(self._active, sd, 1.0)
        Z = ((X - self._mean) / self._sd)[:, self._active]
        A = np.column_stack([np.ones(n), Z])
        q = A.shape[1]

        # Start at the homogeneous MLE. For q == 1 this *is* the answer.
        b = np.zeros(q)
        b[0] = np.log(self.n_events_ / self.exposure_)
        pen = np.full(q, self.l2)
        pen[0] = 0.0

        def objective(beta):
            mu = e * np.exp(A @ beta)
            return poisson_loglik(y, mu) - 0.5 * np.sum(pen * beta**2)

        obj = objective(b)
        for _ in range(self.max_iter):
            mu = e * np.exp(A @ b)
            grad = A.T @ (y - mu) - pen * b
            H = (A * mu[:, None]).T @ A + np.diag(pen)
            step = np.linalg.solve(H, grad)
            t = 1.0
            while True:  # step-halving keeps the likelihood monotone
                b_new = b + t * step
                obj_new = objective(b_new)
                if obj_new >= obj - 1e-12 or t < 1e-8:
                    break
                t *= 0.5
            converged = np.max(np.abs(b_new - b)) < self.tol
            b, obj = b_new, obj_new
            if converged:
                break

        mu = e * np.exp(A @ b)
        H = (A * mu[:, None]).T @ A + np.diag(pen)
        cov_std = np.linalg.inv(H)

        # Map back to raw feature units.
        slopes = np.zeros(p)
        slopes[self._active] = b[1:] / self._sd[self._active]
        self.coef_ = slopes
        self.intercept_ = float(b[0] - np.sum(slopes * self._mean))
        # SEs: delta method for raw slopes (intercept SE reported on centred scale)
        se_slopes = np.zeros(p)
        se_slopes[self._active] = np.sqrt(np.diag(cov_std)[1:]) / self._sd[self._active]
        self.se_ = np.concatenate([[np.sqrt(cov_std[0, 0])], se_slopes])
        self.loglik_ = poisson_loglik(y, mu)
        self._ll_homogeneous = poisson_loglik(y, e * self.homogeneous_rate_)
        self._n_params = q
        return self

    # -- prediction ----------------------------------------------------------
    def predict_rate(self, X) -> np.ndarray:
        """lambda(x): events per unit time (e.g. faults per cell-year)."""
        X = np.asarray(X, dtype=float)
        if X.ndim == 1:
            X = X[:, None] if self.coef_.size == 1 else X[None, :]
        if self.coef_.size == 0:
            return np.full(X.shape[0], np.exp(self.intercept_))
        return np.exp(self.intercept_ + X @ self.coef_)

    def predict_mean(self, X, exposure) -> np.ndarray:
        return self.predict_rate(X) * np.asarray(exposure, dtype=float)

    @property
    def homogeneous_rate_(self) -> float:
        """The simple-Poisson MLE sum(y)/sum(e) on the training data."""
        return self.n_events_ / self.exposure_

    # -- inference -----------------------------------------------------------
    def lrt_vs_homogeneous(self) -> dict:
        """Likelihood-ratio test of H0 'all lambdas equal' (simple Poisson)."""
        lam0 = self.homogeneous_rate_
        stat = max(0.0, 2.0 * (self.loglik_ - self._ll_homogeneous))
        df = self._n_params - 1
        p = float(stats.chi2.sf(stat, df)) if df > 0 else 1.0
        return {"lambda_homogeneous": lam0, "lr_stat": stat, "df": df, "p_value": p}

    def summary(self) -> str:
        names = self.feature_names or [f"x{j}" for j in range(self.coef_.size)]
        lines = [
            f"events = {self.n_events_:.0f}, exposure = {self.exposure_:.1f}, "
            f"homogeneous MLE = {self.homogeneous_rate_:.5f}",
            f"{'term':<22}{'coef':>12}{'se':>12}{'rate ratio':>12}",
            f"{'log lambda_0':<22}{self.intercept_:>12.4f}{self.se_[0]:>12.4f}{'':>12}",
        ]
        for name, c, s in zip(names, self.coef_, self.se_[1:]):
            lines.append(f"{name:<22}{c:>12.4f}{s:>12.4f}{np.exp(c):>12.3f}")
        return "\n".join(lines)


def fit_gradient_boosted_intensity(X, events, exposure, **kwargs):
    """Nonlinear alternative: gradient-boosted trees with Poisson loss.

    Fits the rate y/e with sample weight e, which has the same optimum as the
    Poisson likelihood with a log-exposure offset. Unlike the GLM, there is no
    exact guarantee of collapsing to sum(y)/sum(e) under homogeneous data,
    so use it as a challenger, scored on held-out Poisson deviance.
    """
    from sklearn.ensemble import HistGradientBoostingRegressor

    X = np.asarray(X, dtype=float)
    y = np.asarray(events, dtype=float)
    e = np.asarray(exposure, dtype=float)
    keep = e > 0
    params = dict(loss="poisson", max_iter=200, learning_rate=0.05, max_leaf_nodes=15,
                  min_samples_leaf=200, l2_regularization=1.0, random_state=0)
    params.update(kwargs)
    model = HistGradientBoostingRegressor(**params)
    model.fit(X[keep], y[keep] / e[keep], sample_weight=e[keep])
    return model
