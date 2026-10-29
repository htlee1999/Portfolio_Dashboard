"""Your actual returns, rebuilt from every purchase, every sale and the dividends paid on the shares you held.

Performance's growth chart is a backtest of today's weights; this is what your money actually did:

- **Time-weighted return** chains each day's return, so the size and timing of your deposits don't
  count. It measures the holdings.
- **Money-weighted return** (IRR) is the single annual rate that turns your purchases into your sales,
  dividends and today's value. It measures you, timing included.
- **Same trades in the S&P 500** (a public-market equivalent) puts every purchase into SPY on the same
  day and takes every sale out of it. The gap is what your picks and timing added or cost.

Values are in the base currency, at each day's exchange rate. Dividends are gross (before withholding
tax) and counted as cash received, not reinvested. Lots are taken as entered, in today's share terms.
"""

from concurrent.futures import ThreadPoolExecutor
from datetime import date

import numpy as np
import pandas as pd
from scipy.optimize import brentq

from . import market
from .storage import all_purchases, load_holdings, load_transactions

BENCHMARK = "SPY"


def xirr(flows: list[tuple[pd.Timestamp, float]]) -> float | None:
    """Annual rate at which the flows (negative = money in, positive = money out) net to zero."""
    flows = [(d, a) for d, a in flows if a]
    if len(flows) < 2 or all(a >= 0 for _, a in flows) or all(a <= 0 for _, a in flows):
        return None
    t0 = min(d for d, _ in flows)
    years = np.array([(d - t0).days / 365.25 for d, _ in flows])
    amounts = np.array([a for _, a in flows])
    if years.max() < 1 / 365:
        return None

    def npv(rate: float) -> float:
        return float(np.sum(amounts / (1 + rate) ** years))

    try:
        return brentq(npv, -0.9999, 100.0)
    except ValueError:
        return None


def _on_or_after(index: pd.DatetimeIndex, day) -> int:
    return int(index.searchsorted(pd.Timestamp(day), side="left"))


def rebuild(purchases: list[dict], sales: list[dict], prices: dict[str, pd.Series], divs: dict[str, pd.Series],
            fx: dict[str, pd.Series], bench: pd.Series, bench_fx: pd.Series, index: pd.DatetimeIndex) -> dict:
    """The daily ledger on ``index`` (trading days). ``prices`` are split-adjusted closes in each lot's
    currency; ``fx[currency]`` and ``bench_fx`` are rates to the base currency on ``index``; ``bench``
    is the benchmark's dividend-adjusted close in USD."""
    n = len(index)
    value = np.zeros(n)
    flow = np.zeros(n)        # money put in (+) or taken out (-), in base currency
    income = np.zeros(n)      # dividends received
    by_symbol_income: dict[str, float] = {}
    div_events = []
    symbols = sorted({p["Symbol"] for p in purchases})

    for sym in symbols:
        shares = np.zeros(n)
        ccy = next(p["Currency"] for p in purchases if p["Symbol"] == sym)
        rate = fx[ccy]
        for p in (p for p in purchases if p["Symbol"] == sym):
            i = _on_or_after(index, p["Purchase_Date"])
            if i < n:
                shares[i:] += p["Quantity"]
                flow[i] += p["Quantity"] * p["Purchase_Price"] * rate[i]
        for s in (s for s in sales if s["Symbol"] == sym):
            i = _on_or_after(index, s["Date"])
            if i < n:
                shares[i:] -= s["Quantity"]
                flow[i] -= s["proceeds"] * rate[i]
        shares = np.maximum(shares, 0)
        px = prices.get(sym)
        if px is not None:
            # Before the first close we have (a new listing), value at the first one.
            value += shares * px.reindex(index).ffill().bfill().to_numpy() * rate
        for ex, amount in (divs.get(sym) if divs.get(sym) is not None else pd.Series(dtype=float)).items():
            i = _on_or_after(index, ex)
            # Paid on the shares held at the close before the ex-date.
            if 0 < i < n and shares[i - 1] > 0:
                cash = shares[i - 1] * float(amount) * rate[i]
                income[i] += cash
                by_symbol_income[sym] = by_symbol_income.get(sym, 0.0) + cash
                div_events.append({"symbol": sym, "date": index[i].date().isoformat(), "per_share": float(amount),
                                   "shares": float(shares[i - 1]), "amount": cash, "currency": ccy})

    # Time-weighted: each day's gain over what was invested at its start, with money added that day
    # counted from the start of the day (a Modified Dietz day).
    prev = np.concatenate([[0.0], value[:-1]])
    base = prev + np.maximum(flow, 0)
    gain = value + income - prev - flow
    daily = np.divide(gain, base, out=np.zeros(n), where=base > 0)
    twr = np.cumprod(1 + daily)

    # The same money in and out of the benchmark on the same days.
    b = bench.reindex(index).ffill().bfill().to_numpy() * bench_fx
    units = np.cumsum(flow / b)
    pme = np.maximum(units, 0) * b
    first = int(np.argmax(flow > 0)) if (flow > 0).any() else 0
    bench_twr = b / b[first]

    return {
        "value": value, "flow": flow, "income": income, "twr": twr, "bench_twr": bench_twr, "pme": pme,
        "first": first, "by_symbol_income": by_symbol_income, "div_events": div_events,
    }


def build(username: str, base: str) -> dict:
    purchases = [p for p in all_purchases(username) if p.get("Purchase_Date") and float(p["Quantity"]) > 0]
    sales = [t for t in load_transactions(username) if t.get("type") == "SELL"]
    for p in purchases:
        p["Quantity"], p["Purchase_Price"] = float(p["Quantity"]), float(p["Purchase_Price"])
        p["Currency"] = p.get("Currency") or "USD"
    if not purchases:
        return {"base_currency": base, "empty": True}

    symbols = sorted({p["Symbol"] for p in purchases})
    currencies = sorted({p["Currency"] for p in purchases} | {"USD"})
    with ThreadPoolExecutor(max_workers=8) as pool:
        prices = dict(zip(symbols, pool.map(lambda s: market.raw_closes(s, "10y"), symbols)))
        divs = dict(zip(symbols, pool.map(market.dividends, symbols)))
        fx_raw = dict(zip(currencies, pool.map(lambda c: market.fx_history(c, base), currencies)))
        live = dict(zip(symbols, pool.map(market.price, symbols)))
    bench = market.closes(BENCHMARK, "10y")
    if bench is None:
        raise LookupError("Couldn't fetch S&P 500 (SPY) history. Yahoo Finance may be rate-limiting; try again shortly.")

    start = pd.Timestamp(min(p["Purchase_Date"] for p in purchases))
    index = bench.index[bench.index >= start - pd.Timedelta(days=7)]
    if index.empty:
        raise LookupError("No price history covers your purchases yet.")

    def on_index(ccy: str) -> np.ndarray:
        if ccy == base:
            return np.ones(len(index))
        series = fx_raw.get(ccy)
        if series is None:
            rate = market.fx_rate(ccy, base) or 1.0
            return np.full(len(index), rate)
        return series.reindex(index.union(series.index)).ffill().bfill().reindex(index).to_numpy()

    fx = {c: on_index(c) for c in currencies}
    ledger = rebuild(purchases, sales, prices, divs, fx, bench, fx["USD"], index)

    # Today: value the holdings at live quotes, so the totals match Overview.
    held: dict[str, float] = {}
    for p in purchases:
        held[p["Symbol"]] = held.get(p["Symbol"], 0.0) + p["Quantity"]
    for s in sales:
        held[s["Symbol"]] = held.get(s["Symbol"], 0.0) - s["Quantity"]
    ccy_of = {p["Symbol"]: p["Currency"] for p in purchases}
    value_now = 0.0
    for sym, qty in held.items():
        if qty <= 1e-9:
            continue
        px = live.get(sym) or (float(prices[sym].iloc[-1]) if prices.get(sym) is not None else None)
        if px is not None:
            value_now += qty * px * market.convert(1.0, ccy_of[sym], base)

    flow, income = ledger["flow"], ledger["income"]
    bought = float(flow[flow > 0].sum())
    sold = float(-flow[flow < 0].sum()) + 0.0  # never -0.0
    dividends = float(income.sum())
    today = pd.Timestamp(date.today())

    cash_flows = [(index[i], -float(flow[i])) for i in np.nonzero(flow)[0]]
    cash_flows += [(index[i], float(income[i])) for i in np.nonzero(income)[0]]
    irr = xirr(cash_flows + [(today, value_now)])
    pme_now = float(ledger["pme"][-1])
    bench_irr = xirr([(index[i], -float(flow[i])) for i in np.nonzero(flow)[0]] + [(today, pme_now)])

    first = ledger["first"]
    years = max((index[-1] - index[first]).days / 365.25, 1e-9)
    twr = float(ledger["twr"][-1]) * (value_now / ledger["value"][-1] if ledger["value"][-1] else 1) - 1
    bench_twr = float(ledger["bench_twr"][-1]) - 1

    realized = []
    for s in sales:
        rate_sale = market.fx_on(s["Currency"], base, s["Date"])
        cost_base = sum(lot["Quantity"] * lot["Purchase_Price"] * market.fx_on(lot["Currency"], base, lot["Purchase_Date"])
                        for lot in s.get("lots", []))
        proceeds_base = s["proceeds"] * rate_sale
        realized.append({
            "id": s["id"], "symbol": s["Symbol"], "date": s["Date"], "quantity": s["Quantity"], "price": s["Price"],
            "fees": s.get("Fees", 0.0), "currency": s["Currency"], "proceeds": s["proceeds"], "cost": s["cost"],
            "gain": s["realized"], "gain_pct": s["realized"] / s["cost"] * 100 if s["cost"] else None,
            "gain_base": proceeds_base - cost_base,
            # Held for at least a year, the usual line between short and long-term gains.
            "held_days": min(((pd.Timestamp(s["Date"]) - pd.Timestamp(lot["Purchase_Date"])).days for lot in s.get("lots", [])), default=None),
        })
    realized.sort(key=lambda r: r["date"], reverse=True)

    by_year: dict[str, float] = {}
    for e in ledger["div_events"]:
        by_year[e["date"][:4]] = by_year.get(e["date"][:4], 0.0) + e["amount"]
    ttm = sum(e["amount"] for e in ledger["div_events"] if pd.Timestamp(e["date"]) > today - pd.Timedelta(days=365))

    # Weekly points keep the chart light; the last day is always included.
    keep = sorted(set(range(first, len(index), 5)) | {len(index) - 1})
    net = np.cumsum(flow)
    cum_income = np.cumsum(income)
    series = [{
        "date": index[i].date().isoformat(),
        "value": float(ledger["value"][i]),
        "with_income": float(ledger["value"][i] + cum_income[i]),
        "net_invested": float(net[i]),
        "benchmark_value": float(ledger["pme"][i]),
        "twr": (float(ledger["twr"][i]) - 1) * 100,
        "benchmark_twr": (float(ledger["bench_twr"][i]) - 1) * 100,
    } for i in keep]

    missing = sorted(s for s in symbols if prices.get(s) is None)
    # Against the cost of the lots still held, at the exchange rate of each purchase day.
    unrealized = value_now - sum(float(h["Quantity"]) * float(h["Purchase_Price"]) * market.fx_on(h["Currency"] or "USD", base, h["Purchase_Date"])
                                 for h in load_holdings(username) if h.get("Purchase_Date"))
    return {
        "base_currency": base,
        "empty": False,
        "start": index[first].date().isoformat(),
        "years": years,
        "summary": {
            "bought": bought,
            "sold": sold,
            "value": value_now,
            "dividends": dividends,
            "dividends_ttm": ttm,
            "realized": sum(r["gain_base"] for r in realized),
            "unrealized": unrealized,
            "total_gain": value_now + sold + dividends - bought,
            "twr_pct": twr * 100,
            "twr_annual_pct": ((1 + twr) ** (1 / years) - 1) * 100 if years >= 1 else None,
            "irr_pct": None if irr is None else irr * 100,
            "benchmark_twr_pct": bench_twr * 100,
            "benchmark_irr_pct": None if bench_irr is None else bench_irr * 100,
            "benchmark_value": pme_now,
            # Your holdings plus the dividends they paid, against the same trades made in SPY.
            "value_added": value_now + dividends - pme_now,
        },
        "series": series,
        "dividends": {
            "by_symbol": sorted(({"symbol": k, "amount": v} for k, v in ledger["by_symbol_income"].items()), key=lambda x: -x["amount"]),
            "by_year": [{"year": k, "amount": v} for k, v in sorted(by_year.items())],
            "recent": sorted(ledger["div_events"], key=lambda e: e["date"], reverse=True)[:20],
        },
        "realized": realized,
        "missing": missing,
        "benchmark": BENCHMARK,
    }

