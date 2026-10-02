"""Market data: price history, quotes, company info and FX.

Ports the original Streamlit app's Finnhub-first quote lookup and the Yahoo circuit
breaker (skip Yahoo for a cooldown after it fails, so a rate-limit doesn't make
every request wait for the full network timeout).
"""

import logging
import time

import pandas as pd
import requests
import yfinance as yf

from config import get_finnhub_api_key, is_finnhub_configured, normalize_symbol

from .utils import ttl_cache

logging.getLogger("yfinance").setLevel(logging.CRITICAL)

_YAHOO_COOLDOWN_SECONDS = 300
_yahoo_down_until = 0.0


def yahoo_available() -> bool:
    return time.time() >= _yahoo_down_until


def _trip_yahoo() -> None:
    global _yahoo_down_until
    _yahoo_down_until = time.time() + _YAHOO_COOLDOWN_SECONDS


def _reset_yahoo() -> None:
    global _yahoo_down_until
    _yahoo_down_until = 0.0


@ttl_cache(600)
def history(symbol: str, period: str = "1y") -> pd.DataFrame | None:
    """OHLCV history, or None when Yahoo is unavailable."""
    symbol = normalize_symbol(symbol)
    if not yahoo_available():
        return None
    try:
        data = yf.Ticker(symbol).history(period=period)
    except Exception:
        _trip_yahoo()
        return None
    if data is None or data.empty:
        return None
    _reset_yahoo()
    return data


@ttl_cache(3600)
def raw_closes(symbol: str) -> pd.Series | None:
    """Five years of closes adjusted for splits but not dividends, the prices investors
    actually paid; dividend-adjusted history understates past valuations."""
    symbol = normalize_symbol(symbol)
    if not yahoo_available():
        return None
    try:
        data = yf.Ticker(symbol).history(period="5y", auto_adjust=False)
    except Exception:
        _trip_yahoo()
        return None
    if data is None or data.empty:
        return None
    _reset_yahoo()
    close = data["Close"].dropna()
    close.index = close.index.tz_localize(None)
    return close


@ttl_cache(3600)
def info(symbol: str) -> dict | None:
    """yfinance ``Ticker.info`` (company profile and valuation fields)."""
    symbol = normalize_symbol(symbol)
    if not yahoo_available():
        return None
    try:
        data = yf.Ticker(symbol).info
        _reset_yahoo()
        return data or None
    except Exception:
        _trip_yahoo()
        return None


@ttl_cache(3600)
def statements(symbol: str) -> dict | None:
    """Annual income statement, balance sheet and cash flow."""
    symbol = normalize_symbol(symbol)
    if not yahoo_available():
        return None
    try:
        t = yf.Ticker(symbol)
        result = {"income": t.financials, "balance": t.balance_sheet, "cashflow": t.cashflow}
        _reset_yahoo()
        return result
    except Exception:
        _trip_yahoo()
        return None


@ttl_cache(3600)
def earnings(symbol: str) -> dict | None:
    """Recent EPS against estimates, and how analysts' estimates have moved."""
    symbol = normalize_symbol(symbol)
    if not yahoo_available():
        return None
    t = yf.Ticker(symbol)
    result = {}
    # Each dataset is missing for many non-US listings, so a failure here isn't an outage.
    for key, attr in (("history", "earnings_history"), ("trend", "eps_trend"), ("revisions", "eps_revisions")):
        try:
            frame = getattr(t, attr)
            result[key] = frame if isinstance(frame, pd.DataFrame) and not frame.empty else None
        except Exception:
            result[key] = None
    return result


def _to_finnhub_symbol(symbol: str) -> str | None:
    parts = symbol.rsplit(".", 1)
    if len(parts) == 2 and parts[1].isalpha():
        return None  # exchange-suffixed foreign listing; not on Finnhub's free tier
    return symbol.replace("-", ".")


def _finnhub_price(symbol: str) -> float | None:
    if not is_finnhub_configured():
        return None
    fh_symbol = _to_finnhub_symbol(symbol)
    if fh_symbol is None:
        return None
    for attempt in range(2):
        try:
            response = requests.get(
                "https://finnhub.io/api/v1/quote",
                params={"symbol": fh_symbol, "token": get_finnhub_api_key()},
                timeout=6,
            )
            if response.status_code != 200:
                return None
            price = response.json().get("c")
            return float(price) if price else None
        except Exception:
            if attempt == 0:
                continue
            return None
    return None


@ttl_cache(600)
def price(symbol: str) -> float | None:
    """Latest price: Finnhub first, Yahoo fallback. Failures are not cached."""
    symbol = normalize_symbol(symbol)
    quote = _finnhub_price(symbol)
    if quote is not None:
        return quote
    if yahoo_available():
        try:
            data = yf.Ticker(symbol).history(period="5d")
            if not data.empty:
                _reset_yahoo()
                return float(data["Close"].iloc[-1])
            _trip_yahoo()
        except Exception:
            _trip_yahoo()
    return None


@ttl_cache(3600)
def fx_rate(from_currency: str, to_currency: str) -> float | None:
    if from_currency == to_currency:
        return 1.0
    try:
        data = yf.Ticker(f"{from_currency}{to_currency}=X").history(period="5d")
        if not data.empty:
            return float(data["Close"].iloc[-1])
    except Exception:
        pass
    try:
        response = requests.get(f"https://api.exchangerate-api.com/v4/latest/{from_currency}", timeout=5)
        rate = response.json()["rates"].get(to_currency)
        return float(rate) if rate else None
    except Exception:
        return None


def convert(amount: float, from_currency: str, to_currency: str) -> float:
    rate = fx_rate(from_currency, to_currency)
    # Matches the original app: fall back to 1:1 rather than dropping the holding.
    return amount * (rate if rate is not None else 1.0)
