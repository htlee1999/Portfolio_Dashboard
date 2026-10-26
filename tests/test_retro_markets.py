import numpy as np
import pandas as pd

from backend.retro_markets import EXCLUDE_SHIFT, bh_qvalues, indicator, shift_test


def _windows(n, rng, count=30, length=15):
    x = np.zeros(n, dtype=bool)
    for s in rng.choice(n - length, count, replace=False):
        x[s:s + length] = True
    return x


def test_shift_test_matches_brute_force():
    rng = np.random.default_rng(0)
    y = rng.normal(0, 0.01, 800)
    x = _windows(800, rng)
    observed, p, shifts = shift_test(x, y)
    assert np.isclose(observed, y[x].mean() - y[~x].mean())
    brute = []
    for k in range(800):
        if min(k, 800 - k) < EXCLUDE_SHIFT:
            continue
        xs = np.roll(x, k)
        brute.append(y[xs].mean() - y[~xs].mean())
    assert shifts == len(brute)
    assert np.isclose(p, (1 + np.sum(np.abs(brute) >= abs(observed) - 1e-15)) / (1 + len(brute)))


def test_no_effect_is_rarely_significant():
    rng = np.random.default_rng(1)
    ps = [shift_test(_windows(2000, rng), rng.standard_t(4, 2000) * 0.01)[1] for _ in range(200)]
    assert 0.02 < np.mean(np.array(ps) < 0.05) < 0.10


def test_planted_effect_is_found():
    rng = np.random.default_rng(2)
    x = _windows(3000, rng, count=40, length=20)
    y = rng.normal(0, 0.01, 3000) - 0.004 * x
    assert shift_test(x, y)[1] < 0.01


def test_bh_qvalues():
    q = bh_qvalues([0.01, 0.04, 0.03, 0.5])
    assert np.allclose(q, [0.04, 0.0533333, 0.0533333, 0.5])


def test_indicator_uses_market_close():
    idx = pd.DatetimeIndex(["2025-03-14", "2025-03-17", "2025-04-07", "2025-04-08"])
    # Mercury retrograde 2025-03-15 06:51 UTC to 2025-04-07 11:09 UTC
    w = [(pd.Timestamp("2025-03-15T06:51Z"), pd.Timestamp("2025-04-07T11:09Z"))]
    assert indicator(idx, w).tolist() == [False, True, False, False]
