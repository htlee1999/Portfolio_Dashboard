"""Shared helpers: JSON-safe conversion and a success-only TTL cache."""

import functools
import math
import threading
import time
from datetime import date, datetime
from typing import Any, Callable

import numpy as np
import pandas as pd


def clean(value: Any) -> Any:
    """Recursively convert numpy/pandas values into JSON-safe Python values.

    NaN and infinities become None so the frontend never receives invalid JSON.
    """
    if isinstance(value, dict):
        return {str(k): clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [clean(v) for v in value]
    if isinstance(value, (pd.Timestamp, datetime, date)):
        return value.isoformat()
    if isinstance(value, np.bool_):
        return bool(value)
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, (np.floating, float)):
        f = float(value)
        return None if math.isnan(f) or math.isinf(f) else f
    if isinstance(value, np.ndarray):
        return [clean(v) for v in value.tolist()]
    if value is pd.NaT:
        return None
    return value


def num(value: Any) -> float | None:
    """Coerce to a finite float, or None."""
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(f) or math.isinf(f) else f


def series_points(index, **columns) -> list[dict]:
    """Zip a DatetimeIndex and named series into chart-ready row dicts."""
    rows = []
    for i, ts in enumerate(index):
        row = {"date": pd.Timestamp(ts).strftime("%Y-%m-%d")}
        for name, col in columns.items():
            row[name] = num(col.iloc[i]) if hasattr(col, "iloc") else num(col[i])
        rows.append(row)
    return rows


def ttl_cache(seconds: int) -> Callable:
    """Cache a function's result per-arguments for ``seconds``.

    Only non-None results are cached, so a transient network failure retries on
    the very next call instead of being remembered for the full TTL.
    """

    def decorator(fn: Callable) -> Callable:
        store: dict = {}
        lock = threading.Lock()

        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            key = (args, tuple(sorted(kwargs.items())))
            with lock:
                hit = store.get(key)
                if hit and time.time() - hit[1] < seconds:
                    return hit[0]
            result = fn(*args, **kwargs)
            if result is not None:
                with lock:
                    store[key] = (result, time.time())
            return result

        wrapper.cache_clear = store.clear  # type: ignore[attr-defined]
        return wrapper

    return decorator
