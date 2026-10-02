"""GARCH(1,1) with Student-t errors (Bollerslev 1986, 1987), fitted by maximum likelihood.

Kept dependency-free (numpy + scipy) rather than pulling in the `arch` package and
statsmodels; it matches `arch`'s estimates for the same specification. Returns are in percent.
"""

import math

import numpy as np
from scipy import optimize, signal, special, stats


def _variance(e: np.ndarray, omega: float, alpha: float, beta: float, v0: float) -> np.ndarray:
    """Conditional variance sigma²_t for every t, plus one step past the end."""
    x = np.concatenate([[v0], omega + alpha * e**2])
    return signal.lfilter([1.0], [1.0, -beta], x)


def _neg_loglik(params: np.ndarray, e: np.ndarray, v0: float) -> float:
    omega, alpha, beta, nu = params
    s2 = _variance(e, omega, alpha, beta, v0)[:-1]
    if np.any(s2 <= 0):
        return 1e10
    ll = (special.gammaln((nu + 1) / 2) - special.gammaln(nu / 2) - 0.5 * math.log(math.pi * (nu - 2))
          - 0.5 * np.log(s2) - (nu + 1) / 2 * np.log1p(e**2 / (s2 * (nu - 2))))
    return -float(ll.sum())


def fit(returns: np.ndarray) -> dict:
    """Fit on daily returns in percent. Mean is held constant at the sample mean."""
    mu = float(returns.mean())
    e = returns - mu
    var = float(e.var())
    start = np.array([var * 0.05, 0.08, 0.88, 8.0])
    res = optimize.minimize(
        _neg_loglik, start, args=(e, var), method="SLSQP",
        bounds=[(var * 1e-6, var * 10), (0.0, 0.5), (0.0, 0.999), (2.1, 200.0)],
        constraints=[{"type": "ineq", "fun": lambda p: 0.9999 - p[1] - p[2]}],
    )
    omega, alpha, beta, nu = (float(x) for x in res.x)
    return {"mu": mu, "omega": omega, "alpha": alpha, "beta": beta, "nu": nu, "v0": var}


def one_step_sigma(returns: np.ndarray, p: dict) -> np.ndarray:
    """Standard deviation forecast for the next day, made at the close of each day,
    using parameters `p` (so it can be estimated on one window and applied to later data)."""
    s2 = _variance(returns - p["mu"], p["omega"], p["alpha"], p["beta"], p["v0"])
    return np.sqrt(s2[1:])


def quantile(level: float, nu: float) -> float:
    """Quantile of the unit-variance Student-t used by the model."""
    return float(stats.t.ppf(level, nu) * math.sqrt((nu - 2) / nu))


def coverage_test(hits: np.ndarray, level: float) -> float | None:
    """Kupiec (1995) / Christoffersen (1998) unconditional coverage test: p-value that the
    band's hit rate equals its nominal level."""
    n, x = len(hits), int((~hits).sum())
    if n == 0:
        return None
    p, pi = 1 - level, x / n
    xlogy = special.xlogy  # treats 0·log(0) as 0
    lr = -2 * (xlogy(x, p) + xlogy(n - x, 1 - p) - xlogy(x, pi) - xlogy(n - x, 1 - pi))
    return float(math.erfc(math.sqrt(max(float(lr), 0.0) / 2)))
