"""Forecast: models of the next session's return, judged against a no-change forecast,
plus a GARCH(1,1) range for the next close.

Models predict returns rather than prices: price levels trend, so tree models (which can't
extrapolate past their training range) and regressions on them give misleading fits.
Every model is tested walk-forward: refitted on all data up to a date, then scored only on
the days after it.
"""

import importlib.util
import math
import os
import threading

for _var in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ.setdefault(_var, "1")
# For Chronos: TensorFlow and torch deadlock when both load in one process on macOS, so keep
# transformers on torch; and the Xet transfer backend can stall, so download over plain HTTPS.
os.environ.setdefault("USE_TF", "0")
os.environ.setdefault("USE_FLAX", "0")
os.environ.setdefault("HF_HUB_DISABLE_XET", "1")

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import RidgeCV
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from technical_indicators import TechnicalAnalysis

from . import market, volatility

MIN_ROWS = 200          # labelled rows needed: a training window plus a test window
REFIT_EVERY = 21        # trading days between walk-forward refits (about a month)
BANDS = (0.80, 0.95)
CHRONOS_MODEL = os.getenv("CHRONOS_MODEL", "amazon/chronos-bolt-tiny")


def features(data: pd.DataFrame) -> pd.DataFrame:
    """Scale-free inputs: returns, distances from averages and volatility, so a model
    trained at one price level applies at another."""
    close, high, low, open_ = data["Close"], data["High"], data["Low"], data["Open"]
    ret = close.pct_change()
    macd = close.ewm(span=12).mean() - close.ewm(span=26).mean()
    sma20, std20 = close.rolling(20).mean(), close.rolling(20).std()
    vol20 = ret.rolling(20).std()
    f = pd.DataFrame(index=data.index)
    f["Return, last day"] = ret
    f["Return, last 5 days"] = close.pct_change(5)
    f["Return, last 20 days"] = close.pct_change(20)
    f["Distance from 20-day average"] = close / sma20 - 1
    f["Distance from 50-day average"] = close / close.rolling(50).mean() - 1
    f["RSI (14)"] = TechnicalAnalysis(data).calculate_rsi() / 100
    f["MACD histogram"] = (macd - macd.ewm(span=9).mean()) / close
    f["Bollinger %B"] = (close - (sma20 - 2 * std20)) / (4 * std20)
    f["Volatility (20-day)"] = vol20
    f["Volatility ratio (5 / 20-day)"] = ret.rolling(5).std() / vol20
    f["Day's high-low range"] = (high - low) / close
    f["Overnight gap"] = open_ / close.shift() - 1
    if "Volume" in data and data["Volume"].gt(0).all():
        f["Volume vs 20-day average"] = np.log(data["Volume"] / data["Volume"].rolling(20).mean())
    return f.replace([np.inf, -np.inf], np.nan)


def _models(rf_estimators: int, rf_depth: int) -> dict:
    return {
        "Ridge regression": lambda: make_pipeline(StandardScaler(), RidgeCV(alphas=np.logspace(-1, 5, 25))),
        "Gradient boosting": lambda: HistGradientBoostingRegressor(
            max_depth=3, learning_rate=0.03, max_iter=150, min_samples_leaf=30, l2_regularization=1.0, random_state=42),
        "Random forest": lambda: RandomForestRegressor(
            n_estimators=rf_estimators, max_depth=rf_depth, min_samples_leaf=20, max_features=0.5,
            random_state=42, n_jobs=1),
    }


def _p_normal(z: float) -> float:
    """One-sided p-value for a standard-normal statistic."""
    return 0.5 * math.erfc(z / math.sqrt(2))


def _wilson(hits: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson (1927) 95% interval for a proportion."""
    if n == 0:
        return 0.0, 1.0
    p = hits / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return centre - half, centre + half


def _score(actual: np.ndarray, predicted: np.ndarray) -> dict:
    """Out-of-sample skill against the no-change forecast (a predicted return of zero)."""
    err, err0 = actual - predicted, actual
    sse, sse0 = float((err**2).sum()), float((err0**2).sum())
    # Campbell & Thompson (2008) out-of-sample R²: share of the no-change error removed.
    skill = 1 - sse / sse0 if sse0 > 0 else None
    # Diebold & Mariano (1995) on squared errors, with Harvey et al.'s small-sample correction.
    d = err0**2 - err**2
    n = len(d)
    dm_p_better = dm_p_worse = None
    if n > 10 and d.std(ddof=1) > 0:
        stat = d.mean() / (d.std(ddof=1) / math.sqrt(n)) * math.sqrt((n - 1) / n)
        dm_p_better, dm_p_worse = _p_normal(stat), _p_normal(-stat)
    moved = (actual != 0) & (predicted != 0)
    hits, called = int((np.sign(actual[moved]) == np.sign(predicted[moved])).sum()), int(moved.sum())
    low, high = _wilson(hits, called)
    return {
        "rmse_pct": math.sqrt(sse / n) * 100,
        "mae_pct": float(np.abs(err).mean()) * 100,
        "skill": skill,
        "dm_p": dm_p_better,
        "dm_p_worse": dm_p_worse,
        "directional_accuracy": hits / called if called else None,
        "direction_ci": [low, high] if called else None,
        "direction_n": called,
    }


def _verdict(m: dict, alpha: float) -> str:
    if m["skill"] is not None and m["skill"] > 0 and m["dm_p"] is not None and m["dm_p"] < alpha:
        return "skill"
    if m["skill"] is not None and m["skill"] < 0 and m["dm_p_worse"] is not None and m["dm_p_worse"] < alpha:
        return "worse"
    return "no edge"


def _walk_forward(X: np.ndarray, y: np.ndarray, split: int, make) -> np.ndarray:
    preds = np.empty(len(y) - split)
    for start in range(split, len(y), REFIT_EVERY):
        end = min(start + REFIT_EVERY, len(y))
        model = make().fit(X[:start], y[:start])
        preds[start - split:end - split] = model.predict(X[start:end])
    return preds


# ── Chronos-Bolt (optional): a pretrained time-series transformer, run zero-shot ──

_chronos_lock = threading.RLock()
_chronos_pipe = None


def chronos_status() -> dict:
    if importlib.util.find_spec("chronos") is None:
        return {"available": False, "model": CHRONOS_MODEL, "note": "Install chronos-forecasting to enable"}
    return {"available": True, "model": CHRONOS_MODEL, "note": None}


def _chronos():
    global _chronos_pipe
    with _chronos_lock:
        if _chronos_pipe is None:
            import torch
            from chronos import BaseChronosPipeline
            torch.set_num_threads(2)
            _chronos_pipe = BaseChronosPipeline.from_pretrained(CHRONOS_MODEL, device_map="cpu", torch_dtype=torch.float32)
        return _chronos_pipe


def _chronos_forecast(closes: np.ndarray, ends: range) -> tuple[np.ndarray, np.ndarray]:
    """Median next-day return and the 10%/90% quantile returns, forecast from closes up to each end."""
    import torch
    contexts = [torch.tensor(closes[max(0, t - 512):t + 1], dtype=torch.float32) for t in ends]
    with _chronos_lock:
        q, _ = _chronos().predict_quantiles(contexts, prediction_length=1, quantile_levels=[0.1, 0.5, 0.9])
    q = q[:, 0, :].numpy().astype(float)
    last = closes[list(ends)]
    return q[:, 1] / last - 1, q[:, [0, 2]] / last[:, None] - 1


# ── Main entry point ──

def run(symbol: str, period: str, rf_estimators: int = 200, rf_depth: int = 6,
        test_size: int = 30, use_chronos: bool = False) -> dict | None:
    data = market.history(symbol, period)
    if data is None:
        return None
    feats = features(data)
    closes = data["Close"].astype(float)
    target = closes.shift(-1) / closes - 1
    usable = feats.notna().all(axis=1)
    frame = feats[usable].assign(_target=target[usable])
    labelled = frame.dropna(subset=["_target"])
    if len(labelled) < MIN_ROWS:
        raise ValueError(f"Not enough history: the models need about {MIN_ROWS + 50} trading days. Choose 1Y or longer.")

    cols = list(feats.columns)
    X, y = labelled[cols].values, labelled["_target"].values
    split = max(int((1 - test_size / 100) * len(X)), 120)
    y_test = y[split:]
    test_dates = labelled.index[split:]
    latest = frame[cols].iloc[[-1]].values
    last_close = float(closes.iloc[-1])

    models, series_preds = [], {}
    for name, make in _models(rf_estimators, rf_depth).items():
        preds = _walk_forward(X, y, split, make)
        final = make().fit(X, y)
        next_ret = float(final.predict(latest)[0])
        models.append({"name": name, "kind": "trained", "metrics": _score(y_test, preds),
                       "next_return": next_ret, "next_close": last_close * (1 + next_ret)})
        series_preds[name] = preds
        if name == "Random forest":
            importance = sorted(zip(cols, final.feature_importances_), key=lambda x: -x[1])

    chronos = chronos_status() if use_chronos else None
    if chronos and chronos["available"]:
        try:
            positions = [closes.index.get_loc(d) for d in test_dates] + [len(closes) - 1]
            med, band = _chronos_forecast(closes.values, positions)
            metrics = _score(y_test, med[:-1])
            # Its own 80% range (10th-90th percentile), to set against the GARCH range.
            metrics["band80_hit"] = float(((y_test >= band[:-1, 0]) & (y_test <= band[:-1, 1])).mean())
            models.append({"name": "Chronos-Bolt", "kind": "pretrained", "metrics": metrics,
                           "next_return": float(med[-1]), "next_close": last_close * (1 + float(med[-1]))})
            series_preds["Chronos-Bolt"] = med[:-1]
        except Exception as e:  # download or runtime failure shouldn't sink the other models
            chronos = {**chronos, "available": False, "note": f"Chronos-Bolt failed: {e}"}

    # Several models are tested at once, so require Bonferroni-adjusted significance
    # before calling any of them skilful; otherwise one in twenty passes by luck.
    alpha = 0.05 / len(models)
    for m in models:
        m["metrics"]["verdict"] = _verdict(m["metrics"], alpha)

    ranked = [m for m in models if m["metrics"]["skill"] is not None]
    best = max(ranked, key=lambda m: m["metrics"]["skill"])["name"] if ranked else None
    up_share = float((y_test > 0).sum() / max((y_test != 0).sum(), 1))

    rng = _range(closes, test_dates)
    series = []
    for i, d in enumerate(test_dates):
        row = {"date": d.strftime("%Y-%m-%d"), "actual": float(y_test[i] * 100)}
        for name, preds in series_preds.items():
            row[name] = float(preds[i] * 100)
        series.append(row)

    return {
        "symbol": symbol,
        "period": period,
        "last_close": last_close,
        "last_date": closes.index[-1].strftime("%Y-%m-%d"),
        "samples": {"train": split, "test": len(y_test), "features": len(cols), "refit_every": REFIT_EVERY},
        "baseline": {"name": "No change", "up_share": up_share,
                     "rmse_pct": float(np.sqrt((y_test**2).mean()) * 100)},
        "models": models,
        "best_model": best,
        "any_skill": any(m["metrics"]["verdict"] == "skill" for m in models),
        "alpha": alpha,
        "range": rng,
        "series": series,
        "feature_importance": [{"feature": f, "importance": float(i)} for f, i in importance],
        "chronos": chronos,
    }


def _range(closes: pd.Series, test_dates: pd.Index) -> dict:
    """GARCH(1,1) range for the next close, and how often past ranges held the actual close.
    The backtest uses parameters fitted only on data before the test window."""
    rets = closes.pct_change().dropna() * 100
    params = volatility.fit(rets.values[:rets.index.get_loc(test_dates[0])])
    sigma = volatility.one_step_sigma(rets.values, params)  # sigma[i] forecasts the day after rets[i]

    backtest, coverage = [], {}
    hits = {lvl: [] for lvl in BANDS}
    for d in test_dates:
        i = rets.index.get_loc(d)
        if i + 1 >= len(rets):
            break
        prev, actual, s = float(closes.loc[d]), float(closes.iloc[closes.index.get_loc(d) + 1]), sigma[i]
        row = {"date": closes.index[closes.index.get_loc(d) + 1].strftime("%Y-%m-%d"), "actual": actual}
        for lvl in BANDS:
            lo_q, hi_q = volatility.quantile((1 - lvl) / 2, params["nu"]), volatility.quantile((1 + lvl) / 2, params["nu"])
            lo, hi = prev * (1 + (params["mu"] + lo_q * s) / 100), prev * (1 + (params["mu"] + hi_q * s) / 100)
            row[f"lo{int(lvl * 100)}"], row[f"hi{int(lvl * 100)}"] = lo, hi
            hits[lvl].append(lo <= actual <= hi)
        backtest.append(row)
    for lvl in BANDS:
        h = np.array(hits[lvl])
        coverage[str(int(lvl * 100))] = {"target": lvl, "hit_rate": float(h.mean()) if len(h) else None,
                                         "n": len(h), "p_value": volatility.coverage_test(h, lvl)}

    # Tomorrow's range comes from a fit on all the data.
    full = volatility.fit(rets.values)
    s_next = float(volatility.one_step_sigma(rets.values, full)[-1])
    last = float(closes.iloc[-1])
    next_bands = {}
    for lvl in BANDS:
        lo_q, hi_q = volatility.quantile((1 - lvl) / 2, full["nu"]), volatility.quantile((1 + lvl) / 2, full["nu"])
        next_bands[str(int(lvl * 100))] = {"low": last * (1 + (full["mu"] + lo_q * s_next) / 100),
                                           "high": last * (1 + (full["mu"] + hi_q * s_next) / 100)}
    long_run = full["omega"] / (1 - full["alpha"] - full["beta"]) if full["alpha"] + full["beta"] < 1 else None
    return {
        "model": "GARCH(1,1), Student-t",
        "sigma_pct": s_next,
        "long_run_sigma_pct": math.sqrt(long_run) if long_run else None,
        "persistence": full["alpha"] + full["beta"],
        "next": next_bands,
        "coverage": coverage,
        "backtest": backtest,
    }


def quick(symbol: str) -> dict | None:
    """Summary for the AI assessment, always on two years so the models have enough data."""
    try:
        result = run(symbol, "2y")
    except ValueError:
        return None
    if not result:
        return None
    best = next((m for m in result["models"] if m["name"] == result["best_model"]), None)
    return {
        "any_skill": result["any_skill"],
        "test_days": result["samples"]["test"],
        "up_share": result["baseline"]["up_share"],
        "models": [{"name": m["name"], "skill": m["metrics"]["skill"], "dm_p": m["metrics"]["dm_p"],
                    "verdict": m["metrics"]["verdict"], "directional_accuracy": m["metrics"]["directional_accuracy"],
                    "direction_ci": m["metrics"]["direction_ci"], "next_return": m["next_return"]}
                   for m in result["models"]],
        "best": best and {"name": best["name"], "skill": best["metrics"]["skill"], "verdict": best["metrics"]["verdict"],
                          "next_return": best["next_return"]},
        "last_close": result["last_close"],
        "range": {k: v for k, v in result["range"].items() if k != "backtest"},
    }
