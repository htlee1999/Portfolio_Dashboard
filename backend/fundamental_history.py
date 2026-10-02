"""Ratios at each past fiscal year-end, so today's figures can be read against the
company's own history rather than one fixed threshold for every company."""

import statistics

import pandas as pd

from .quality import _div, _get
from .utils import num

# key, label, unit, which direction is favourable, the matching trailing-12-month ratio key
_ROWS = [
    ("pe", "P/E", "x", "lower", "trailingPE"),
    ("pb", "Price / book", "x", "lower", "priceToBook"),
    ("ps", "Price / sales", "x", "lower", "priceToSalesTrailing12Months"),
    ("ev_ebitda", "EV / EBITDA", "x", "lower", "enterpriseToEbitda"),
    ("fcf_yield", "FCF yield", "fraction", "higher", "fcfYield"),
    ("gross_margin", "Gross margin", "fraction", "higher", "grossMargins"),
    ("operating_margin", "Operating margin", "fraction", "higher", "operatingMargins"),
    ("net_margin", "Profit margin", "fraction", "higher", "profitMargins"),
    ("roe", "Return on equity", "fraction", "higher", "returnOnEquity"),
    ("roa", "Return on assets", "fraction", "higher", "returnOnAssets"),
    ("revenue_growth", "Revenue growth", "fraction", "higher", None),
    ("debt_equity", "Debt / equity", "x", "lower", "debtToEquity"),
]
_VALUATION = {"pe", "pb", "ps", "ev_ebitda", "fcf_yield"}
_NOT_FOR_FINANCIALS = {"ev_ebitda", "fcf_yield", "gross_margin", "operating_margin", "debt_equity"}


def _positive(value: float | None) -> float | None:
    return value if value is not None and value > 0 else None


def _year_values(stmts: dict, closes: pd.Series | None, market_cap: float | None, fx: float | None) -> list[dict]:
    """Ratios for each fiscal year, newest first. Market cap at each year-end is today's
    (in the reporting currency) scaled by the price change and the change in share count,
    which avoids ADR share ratios; it ignores past exchange-rate moves."""
    inc, bal, cf = stmts.get("income"), stmts.get("balance"), stmts.get("cashflow")
    if inc is None or inc.empty:
        return []
    price_now = float(closes.iloc[-1]) if closes is not None and len(closes) else None
    shares_now = _get(bal, "Ordinary Shares Number") or _get(bal, "Share Issued")
    cap_now = market_cap * fx if market_cap and fx else None

    years = []
    for i, end in enumerate(inc.columns[:4]):
        revenue = _get(inc, "Total Revenue", i)
        if revenue is None:
            continue
        net_income = _get(inc, "Net Income Common Stockholders", i) or _get(inc, "Net Income", i)
        equity, assets = _get(bal, "Stockholders Equity", i), _get(bal, "Total Assets", i)
        debt = _get(bal, "Total Debt", i)
        cash = _get(bal, "Cash Cash Equivalents And Short Term Investments", i) or _get(bal, "Cash And Cash Equivalents", i)
        ebitda, fcf = _get(inc, "EBITDA", i), _get(cf, "Free Cash Flow", i)

        cap = None
        prior = closes.loc[:pd.Timestamp(end)] if closes is not None else None
        if cap_now and price_now and prior is not None and len(prior) and pd.Timestamp(end) - prior.index[-1] < pd.Timedelta(days=7):
            shares = _get(bal, "Ordinary Shares Number", i) or _get(bal, "Share Issued", i)
            share_ratio = _div(shares, shares_now) if shares and shares_now else 1.0
            if share_ratio and 0.5 < share_ratio < 2:
                cap = cap_now * float(prior.iloc[-1]) / price_now * share_ratio
        ev = None if cap is None or debt is None or cash is None else cap + debt - cash
        prev_revenue = _get(inc, "Total Revenue", i + 1)

        years.append({
            "year": pd.Timestamp(end).strftime("%Y"),
            "pe": _positive(_div(cap, _positive(net_income))),
            "pb": _positive(_div(cap, _positive(equity))),
            "ps": _div(cap, revenue),
            "ev_ebitda": _positive(_div(ev, _positive(ebitda))),
            "fcf_yield": _div(fcf, cap),
            "gross_margin": _div(_get(inc, "Gross Profit", i), revenue),
            "operating_margin": _div(_get(inc, "Operating Income", i), revenue),
            "net_margin": _div(net_income, revenue),
            "roe": _div(net_income, _positive(equity)),
            "roa": _div(net_income, assets),
            "revenue_growth": None if not prev_revenue or prev_revenue <= 0 else revenue / prev_revenue - 1,
            "debt_equity": _div(debt, _positive(equity)),
        })
    return years


def build(stmts: dict, closes: pd.Series | None, ratios: dict, market_cap: float | None,
          fx: float | None, kind: str) -> dict:
    """Each measure by fiscal year (oldest first), today's trailing figure, and where today
    sits against the median of past years."""
    years = list(reversed(_year_values(stmts, closes, market_cap, fx)))
    rows = []
    for key, label, unit, better, ratio_key in _ROWS:
        if kind == "financial" and key in _NOT_FOR_FINANCIALS:
            continue
        values = [num(y[key]) for y in years]
        past = [v for v in values if v is not None]
        if len(past) < 2:
            continue
        now = ratios.get(ratio_key) if ratio_key else None
        if key == "debt_equity" and now is not None:
            now = now / 100  # Yahoo reports debt/equity in percent
        median = statistics.median(past)
        # Relative gap only means something for positive, same-signed figures.
        vs = now / median - 1 if now is not None and median > 0 and now > 0 else None
        verdict = None
        if vs is not None and abs(vs) >= 0.1:
            favourable = (vs < 0) == (better == "lower")
            if key in _VALUATION:
                verdict = "cheaper" if favourable else "pricier"
            else:
                verdict = "better" if favourable else "worse"
        elif vs is not None:
            verdict = "in line"
        rows.append({
            "key": key, "label": label, "unit": unit, "better": better, "valuation": key in _VALUATION,
            "values": values, "now": now, "median": median, "low": min(past), "high": max(past),
            "vs_median": vs, "verdict": verdict,
        })
    return {"years": [y["year"] for y in years], "rows": rows}
