"""Technical analysis: indicator series, current signals and CSV export."""

import math

import pandas as pd

from technical_indicators import TechnicalAnalysis

from . import market
from .utils import num, series_points

# Indicators are computed on at least two years of history so that the 200-day SMA,
# 12-1 momentum and 52-week high are defined, then trimmed to the requested window.
_WINDOW_MONTHS = {"1mo": 1, "3mo": 3, "6mo": 6, "1y": 12}


def _history(symbol: str, period: str) -> pd.DataFrame | None:
    return market.history(symbol, "2y" if period in _WINDOW_MONTHS else "5y")


def _trim(frame: pd.DataFrame, period: str) -> pd.DataFrame:
    months = _WINDOW_MONTHS.get(period)
    if months is None:
        return frame
    return frame[frame.index > frame.index[-1] - pd.DateOffset(months=months)]


def _quote(data: pd.DataFrame) -> dict:
    close = data["Close"]
    last, prev = float(close.iloc[-1]), float(close.iloc[-2]) if len(close) > 1 else float(close.iloc[-1])
    return {
        "price": last,
        "change": last - prev,
        "change_pct": (last - prev) / prev * 100 if prev else 0.0,
        "volume": num(data["Volume"].iloc[-1]) if "Volume" in data else None,
    }


def analyze(symbol: str, period: str, rsi_period: int, macd_fast: int, macd_slow: int,
            bb_period: int, bb_std: float) -> dict | None:
    data = _history(symbol, period)
    if data is None or len(data) < 2:
        return None

    ta = TechnicalAnalysis(data)
    rsi = ta.calculate_rsi(rsi_period)
    macd, signal, hist = ta.calculate_macd(macd_fast, macd_slow)
    upper, middle, lower, pct_b, width = ta.calculate_bollinger_bands(bb_period, bb_std)
    mas = ta.calculate_moving_averages([20, 50, 200])
    obv = ta.calculate_obv()
    obv_ema = obv.ewm(span=10).mean()
    adx, plus_di, minus_di = ta.calculate_adx()
    atr = ta.calculate_atr()
    momentum = ta.calculate_momentum()
    high_52w, dist_52w = ta.calculate_52w_high_distance()
    close = data["Close"]
    price = float(close.iloc[-1])

    rsi_now, macd_now, signal_now, pct_b_now = (num(s.iloc[-1]) for s in (rsi, macd, signal, pct_b))
    adx_now, plus_now, minus_now, atr_now = (num(s.iloc[-1]) for s in (adx, plus_di, minus_di, atr))
    momentum_now, dist_now = num(momentum.iloc[-1]), num(dist_52w.iloc[-1])
    sma50_now, sma200_now = num(mas["SMA_50"].iloc[-1]), num(mas["SMA_200"].iloc[-1])

    def ma_state(name: str) -> dict:
        value = num(mas[name].iloc[-1])
        return {"value": value, "price_above": value is not None and price > value}

    signals = {
        "rsi": {
            "value": rsi_now,
            "state": None if rsi_now is None else "overbought" if rsi_now > 70 else "oversold" if rsi_now < 30 else "neutral",
        },
        "macd": {
            "macd": macd_now,
            "signal": signal_now,
            "state": None if macd_now is None or signal_now is None else "bullish" if macd_now > signal_now else "bearish",
        },
        "bollinger": {
            "percent_b": pct_b_now,
            "state": None if pct_b_now is None else "above" if pct_b_now > 1 else "below" if pct_b_now < 0 else "within",
            "upper": num(upper.iloc[-1]), "middle": num(middle.iloc[-1]), "lower": num(lower.iloc[-1]),
        },
        "trend": {
            "sma20": ma_state("SMA_20"),
            "sma50": ma_state("SMA_50"),
            "sma200": ma_state("SMA_200"),
            "golden_cross": None if sma50_now is None or sma200_now is None else sma50_now > sma200_now,
        },
        "obv": {"value": num(obv.iloc[-1]), "state": "rising" if obv.iloc[-1] > obv_ema.iloc[-1] else "falling"},
        "adx": {
            "value": adx_now,
            "plus_di": plus_now,
            "minus_di": minus_now,
            # Wilder's conventions: above 25 a trend is in place, below 20 the market is ranging
            "state": None if adx_now is None else "strong" if adx_now >= 25 else "weak" if adx_now < 20 else "developing",
            "direction": None if plus_now is None or minus_now is None else "up" if plus_now > minus_now else "down",
        },
        "atr": {"value": atr_now, "pct": None if atr_now is None else atr_now / price * 100},
        "momentum": {
            "return_12_1": momentum_now,
            "state": None if momentum_now is None else "positive" if momentum_now > 0 else "negative",
        },
        "high_52w": {
            "value": num(high_52w.iloc[-1]),
            "distance": dist_now,
            "state": None if dist_now is None else "near" if dist_now >= -0.05 else "far" if dist_now <= -0.25 else "below",
        },
    }

    columns = pd.DataFrame({
        "close": close, "volume": data["Volume"],
        "rsi": rsi, "macd": macd, "signal": signal, "hist": hist,
        "bb_upper": upper, "bb_middle": middle, "bb_lower": lower,
        "sma20": mas["SMA_20"], "sma50": mas["SMA_50"], "sma200": mas["SMA_200"], "ema20": mas["EMA_20"],
        "obv": obv, "obv_ema": obv_ema,
        "adx": adx, "plus_di": plus_di, "minus_di": minus_di, "atr_pct": atr / close * 100,
    })
    window = _trim(columns, period)

    return {
        "symbol": symbol,
        "period": period,
        "quote": _quote(data),
        "signals": signals,
        "series": series_points(window.index, **{name: window[name] for name in window.columns}),
    }


HORIZONS = (5, 20, 60)
_COOLDOWN = 10  # trading days before the same signal can fire again, so one episode counts once
_MIN_EVENTS = 8


def _onsets(condition: pd.Series, defined: pd.Series) -> pd.Series:
    """Days a condition turns true, ignoring the first day an indicator becomes defined."""
    prev_defined = defined & defined.shift(1, fill_value=False)
    return condition & ~condition.shift(1, fill_value=False) & prev_defined


def _debounce(events: pd.Series) -> list[int]:
    kept: list[int] = []
    for i in events.to_numpy().nonzero()[0]:
        if not kept or i - kept[-1] >= _COOLDOWN:
            kept.append(int(i))
    return kept


def backtest(symbol: str, rsi_period: int, macd_fast: int, macd_slow: int,
             bb_period: int, bb_std: float) -> dict | None:
    """How this stock moved 5, 20 and 60 trading days after each signal fired over five
    years, against the baseline of all days. Direction is the signal's conventional reading."""
    data = market.history(symbol, "5y")
    if data is None or len(data) < 100:
        return None

    ta = TechnicalAnalysis(data)
    close, high = data["Close"], data["High"]
    rsi = ta.calculate_rsi(rsi_period)
    macd, signal, _ = ta.calculate_macd(macd_fast, macd_slow)
    upper, _, lower, _, _ = ta.calculate_bollinger_bands(bb_period, bb_std)
    mas = ta.calculate_moving_averages([50, 200])
    sma50, sma200 = mas["SMA_50"], mas["SMA_200"]
    adx, plus_di, minus_di = ta.calculate_adx()
    prior_high = high.rolling(252, min_periods=252).max().shift(1)

    has = lambda *series: pd.concat(series, axis=1).notna().all(axis=1)  # noqa: E731
    specs = [
        ("rsi_oversold", "rsi", "RSI falls below 30", "up", rsi < 30, has(rsi)),
        ("rsi_overbought", "rsi", "RSI rises above 70", "down", rsi > 70, has(rsi)),
        ("macd_bull", "macd", "MACD crosses above signal", "up", macd > signal, has(macd, signal)),
        ("macd_bear", "macd", "MACD crosses below signal", "down", macd < signal, has(macd, signal)),
        ("bb_below", "bollinger", "Close below lower band", "up", close < lower, has(lower)),
        ("bb_above", "bollinger", "Close above upper band", "down", close > upper, has(upper)),
        ("above_200", "sma200", "Close crosses above SMA 200", "up", close > sma200, has(sma200)),
        ("below_200", "sma200", "Close crosses below SMA 200", "down", close < sma200, has(sma200)),
        ("golden_cross", "sma200", "Golden cross (SMA 50 > 200)", "up", sma50 > sma200, has(sma50, sma200)),
        ("death_cross", "sma200", "Death cross (SMA 50 < 200)", "down", sma50 < sma200, has(sma50, sma200)),
        ("high_52w", "high52w", "Close at new 52-week high", "up", close > prior_high, has(prior_high)),
        ("adx_up", "adx", "Strong uptrend begins (ADX > 25, +DI)", "up", (adx > 25) & (plus_di > minus_di), has(adx, plus_di, minus_di)),
        ("adx_down", "adx", "Strong downtrend begins (ADX > 25, −DI)", "down", (adx > 25) & (minus_di > plus_di), has(adx, plus_di, minus_di)),
    ]

    forward = {h: (close.shift(-h) / close - 1) for h in HORIZONS}
    baseline = {h: forward[h].dropna() for h in HORIZONS}

    def stats(idx: list[int], expect: str) -> list[dict]:
        rows = []
        for h in HORIZONS:
            returns = forward[h].iloc[idx].dropna()
            base = baseline[h]
            sign = 1 if expect == "up" else -1
            p0 = float(((base * sign) > 0).mean())
            n = len(returns)
            hit = float(((returns * sign) > 0).mean()) if n else None
            # One-sided z-test of the hit rate against the all-days base rate. Windows overlap,
            # so this overstates confidence; it is a screen, not proof.
            z = (hit - p0) / math.sqrt(p0 * (1 - p0) / n) if n and 0 < p0 < 1 else None
            rows.append({
                "days": h, "n": n, "hit_rate": hit,
                "avg_return": num(returns.mean()) if n else None,
                "baseline_hit": p0, "baseline_avg": num(base.mean()),
                "verdict": "insufficient" if n < _MIN_EVENTS or z is None
                else "worked" if z >= 1.65 else "failed" if z <= -1.65 else "no_edge",
            })
        return rows

    signals = []
    for sid, indicator, label, expect, condition, defined in specs:
        idx = _debounce(_onsets(condition.fillna(False), defined))
        signals.append({
            "id": sid, "indicator": indicator, "label": label, "expect": expect,
            "count": len(idx),
            "last": pd.Timestamp(close.index[idx[-1]]).strftime("%Y-%m-%d") if idx else None,
            "horizons": stats(idx, expect),
        })

    return {
        "symbol": symbol,
        "start": pd.Timestamp(close.index[0]).strftime("%Y-%m-%d"),
        "end": pd.Timestamp(close.index[-1]).strftime("%Y-%m-%d"),
        "horizons": list(HORIZONS),
        "cooldown_days": _COOLDOWN,
        "min_events": _MIN_EVENTS,
        "signals": signals,
    }


def export_csv(symbol: str, period: str) -> str | None:
    data = _history(symbol, period)
    if data is None:
        return None
    return _trim(TechnicalAnalysis(data).add_all_indicators(), period).to_csv()
