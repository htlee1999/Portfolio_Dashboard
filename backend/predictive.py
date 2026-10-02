"""Predictive analysis: Random Forest (+ Decision Tree) ensemble and SVM.

Both models predict the next session's close from technical features, trained
on a chronological split (no shuffling, so the test set is strictly later).
"""

import os

for _var in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ.setdefault(_var, "1")

import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import accuracy_score, mean_absolute_error, mean_squared_error
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVR
from sklearn.tree import DecisionTreeRegressor

from technical_indicators import PredictiveAnalysis

from . import market

_PRICE_COLUMNS = {"Open", "High", "Low", "Close", "Volume", "Dividends", "Stock Splits", "Capital Gains"}


def _evaluate(actual: np.ndarray, predicted: np.ndarray) -> dict:
    direction_ok = accuracy_score(np.diff(actual) > 0, np.diff(predicted) > 0) if len(actual) > 1 else None
    return {
        "rmse": float(np.sqrt(mean_squared_error(actual, predicted))),
        "mae": float(mean_absolute_error(actual, predicted)),
        "directional_accuracy": float(direction_ok) if direction_ok is not None else None,
    }


def prepare(symbol: str, period: str):
    data = market.history(symbol, period)
    if data is None:
        return None
    features = PredictiveAnalysis(data).prepare_features()
    feature_cols = [c for c in features.columns if c not in _PRICE_COLUMNS]
    frame = features.copy()
    frame["Target"] = frame["Close"].shift(-1)
    latest = frame[feature_cols].iloc[[-1]].values
    last_close = float(frame["Close"].iloc[-1])
    frame = frame.dropna(subset=["Target"])
    return frame, feature_cols, latest, last_close


def run(symbol: str, period: str, rf_estimators: int = 100, rf_depth: int = 10,
        svm_c: float = 1.0, svm_gamma: str | float = "scale", test_size: int = 20) -> dict | None:
    prepared = prepare(symbol, period)
    if prepared is None:
        return None
    frame, feature_cols, latest, last_close = prepared
    if len(frame) < 40:
        raise ValueError("Not enough history to train models — choose a longer period.")

    X, y = frame[feature_cols].values, frame["Target"].values
    split = int((1 - test_size / 100) * len(X))
    X_train, X_test, y_train, y_test = X[:split], X[split:], y[:split], y[split:]
    dates = [d.strftime("%Y-%m-%d") for d in frame.index[split:]]

    rf = RandomForestRegressor(n_estimators=rf_estimators, max_depth=rf_depth, random_state=42, n_jobs=1)
    dt = DecisionTreeRegressor(max_depth=rf_depth, random_state=42)
    rf.fit(X_train, y_train)
    dt.fit(X_train, y_train)
    rf_pred = (rf.predict(X_test) + dt.predict(X_test)) / 2
    rf_next = float((rf.predict(latest)[0] + dt.predict(latest)[0]) / 2)

    scaler = StandardScaler().fit(X_train)
    svm = SVR(kernel="rbf", C=svm_c, gamma=svm_gamma)
    svm.fit(scaler.transform(X_train), y_train)
    svm_pred = svm.predict(scaler.transform(X_test))
    svm_next = float(svm.predict(scaler.transform(latest))[0])

    importance = sorted(zip(feature_cols, rf.feature_importances_), key=lambda x: -x[1])

    models = [
        {"name": "Random Forest", "metrics": _evaluate(y_test, rf_pred), "next_close": rf_next},
        {"name": "SVM", "metrics": _evaluate(y_test, svm_pred), "next_close": svm_next},
    ]
    best = min(models, key=lambda m: m["metrics"]["rmse"])["name"]

    return {
        "symbol": symbol,
        "period": period,
        "last_close": last_close,
        "samples": {"train": len(X_train), "test": len(X_test), "features": len(feature_cols)},
        "models": models,
        "best_model": best,
        "series": [
            {"date": d, "actual": float(a), "rf": float(r), "svm": float(s)}
            for d, a, r, s in zip(dates, y_test, rf_pred, svm_pred)
        ],
        "feature_importance": [{"feature": f, "importance": float(i)} for f, i in importance],
    }


def quick(symbol: str, period: str) -> dict | None:
    """Default-parameter Random Forest summary used by the AI assessment."""
    try:
        result = run(symbol, period)
    except ValueError:
        return None
    if not result:
        return None
    rf = result["models"][0]
    return {
        "rmse": rf["metrics"]["rmse"],
        "mae": rf["metrics"]["mae"],
        "directional_accuracy": rf["metrics"]["directional_accuracy"],
        "next_close": rf["next_close"],
        "last_close": result["last_close"],
        "top_features": result["feature_importance"][:5],
    }
