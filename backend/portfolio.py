"""Portfolio valuation, performance vs benchmark, risk and sector breakdown."""

from concurrent.futures import ThreadPoolExecutor

import numpy as np
import pandas as pd

from . import market
from .storage import load_holdings
from .utils import num


def _prices_for(symbols: list[str]) -> dict[str, float | None]:
    unique = sorted(set(symbols))
    with ThreadPoolExecutor(max_workers=8) as pool:
        return dict(zip(unique, pool.map(market.price, unique)))


def metrics(username: str, base_currency: str) -> dict:
    """Aggregate value and per-holding breakdown, converted to ``base_currency``."""
    holdings = load_holdings(username)
    prices = _prices_for([h["Symbol"] for h in holdings])

    rows, unpriced = [], []
    total_invested = total_value = 0.0
    for index, h in enumerate(holdings):
        current = prices.get(h["Symbol"])
        if current is None:
            unpriced.append(h["Symbol"])
            continue
        qty, cost, ccy = float(h["Quantity"]), float(h["Purchase_Price"]), h["Currency"] or "USD"
        invested = qty * cost
        value = qty * current
        invested_base = market.convert(invested, ccy, base_currency)
        value_base = market.convert(value, ccy, base_currency)
        rows.append({
            "index": index,
            "symbol": h["Symbol"],
            "quantity": qty,
            "currency": ccy,
            "purchase_price": cost,
            "purchase_date": h["Purchase_Date"],
            "current_price": current,
            "invested": invested,
            "value": value,
            "gain": value - invested,
            "invested_base": invested_base,
            "value_base": value_base,
            "gain_base": value_base - invested_base,
            "gain_pct": (value - invested) / invested * 100 if invested else 0.0,
        })
        total_invested += invested_base
        total_value += value_base

    for row in rows:
        row["weight"] = row["value_base"] / total_value * 100 if total_value else 0.0

    gain = total_value - total_invested
    return {
        "base_currency": base_currency,
        "holdings_count": len(holdings),
        "total_invested": total_invested,
        "total_value": total_value,
        "total_gain": gain,
        "total_gain_pct": gain / total_invested * 100 if total_invested else 0.0,
        "rows": rows,
        "unpriced": sorted(set(unpriced)),
    }


def performance(username: str, base_currency: str, period: str) -> dict:
    """Normalized performance vs S&P 500, risk metrics, sectors and summary."""
    snapshot = metrics(username, base_currency)
    symbols = sorted({r["symbol"] for r in snapshot["rows"]})

    with ThreadPoolExecutor(max_workers=8) as pool:
        histories = dict(zip(symbols, pool.map(lambda s: market.history(s, period), symbols)))
        risk_histories = dict(zip(symbols, pool.map(lambda s: market.history(s, "1y"), symbols)))
        infos = dict(zip(symbols, pool.map(market.info, symbols)))
    benchmark = market.history("^GSPC", period)

    # Rebased-to-100 series, aligned on calendar date across all tickers.
    frames = {}
    if benchmark is not None:
        frames["S&P 500"] = benchmark["Close"] / benchmark["Close"].iloc[0] * 100
    for sym, data in histories.items():
        if data is not None and not data.empty:
            frames[sym] = data["Close"] / data["Close"].iloc[0] * 100
    value_by_symbol: dict[str, float] = {}
    for r in snapshot["rows"]:
        value_by_symbol[r["symbol"]] = value_by_symbol.get(r["symbol"], 0.0) + r["value_base"]

    series = []
    if frames:
        combined = pd.DataFrame({k: v.set_axis(v.index.tz_localize(None).normalize()) for k, v in frames.items()})
        combined = combined.sort_index().ffill()
        # Today's allocation held constant over the period (a backtest of current weights).
        held = [s for s in symbols if s in combined.columns]
        if held:
            weights = pd.Series({s: value_by_symbol.get(s, 0.0) for s in held})
            present = combined[held].notna()
            weighted = combined[held].fillna(0).mul(weights, axis=1).sum(axis=1)
            combined.insert(0, "Portfolio", weighted / present.mul(weights, axis=1).sum(axis=1))
            frames = {"Portfolio": None, **frames}
        for ts, row in combined.iterrows():
            series.append({"date": ts.strftime("%Y-%m-%d"), **{k: num(v) for k, v in row.items()}})

    risk = []
    for sym, data in risk_histories.items():
        if data is None or data.empty:
            continue
        returns = data["Close"].pct_change().dropna()
        risk.append({
            "symbol": sym,
            "volatility": num(returns.std() * np.sqrt(252) * 100),
            "avg_daily_return": num(returns.mean() * 100),
        })

    sectors: dict[str, float] = {}
    for sym, value in value_by_symbol.items():
        sector = (infos.get(sym) or {}).get("sector") or ("ETF / Fund" if (infos.get(sym) or {}).get("quoteType") == "ETF" else "Unknown")
        sectors[sector] = sectors.get(sector, 0.0) + value
    sector_list = sorted(({"sector": k, "value": v} for k, v in sectors.items()), key=lambda x: -x["value"])

    best = max(snapshot["rows"], key=lambda r: r["gain_pct"], default=None)
    worst = min(snapshot["rows"], key=lambda r: r["gain_pct"], default=None)

    return {
        "period": period,
        "series": series,
        "series_keys": list(frames.keys()),
        "risk": risk,
        "sectors": sector_list,
        "summary": {
            "total_value": snapshot["total_value"],
            "total_invested": snapshot["total_invested"],
            "total_gain": snapshot["total_gain"],
            "total_gain_pct": snapshot["total_gain_pct"],
            "best": best and {"symbol": best["symbol"], "gain_pct": best["gain_pct"]},
            "worst": worst and {"symbol": worst["symbol"], "gain_pct": worst["gain_pct"]},
            "holdings": len(snapshot["rows"]),
        },
        "base_currency": base_currency,
        "unpriced": snapshot["unpriced"],
    }
