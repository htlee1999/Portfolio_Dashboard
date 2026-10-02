"""Fundamental analysis: profile, ratios, statements and analyst view."""

import pandas as pd

from . import fundamental_history, market, quality
from .utils import num

# Display name -> (yfinance info key, unit). "fraction" values are 0.25 == 25%.
# Growth figures from Yahoo compare the latest quarter with the same quarter a year earlier.
RATIO_GROUPS = {
    "Valuation": [
        ("P/E", "trailingPE", "x"),
        ("Forward P/E", "forwardPE", "x"),
        ("PEG", "pegRatio", "x"),
        ("Price / Book", "priceToBook", "x"),
        ("Price / Sales", "priceToSalesTrailing12Months", "x"),
        ("EV / Revenue", "enterpriseToRevenue", "x"),
        ("EV / EBITDA", "enterpriseToEbitda", "x"),
        ("FCF yield", "fcfYield", "fraction"),
    ],
    "Profitability": [
        ("Return on Equity", "returnOnEquity", "fraction"),
        ("Return on Assets", "returnOnAssets", "fraction"),
        ("Gross Margin", "grossMargins", "fraction"),
        ("Operating Margin", "operatingMargins", "fraction"),
        ("Profit Margin", "profitMargins", "fraction"),
    ],
    "Liquidity": [
        ("Current Ratio", "currentRatio", "x"),
        ("Quick Ratio", "quickRatio", "x"),
    ],
    "Leverage": [
        ("Debt / Equity", "debtToEquity", "percent"),
        ("Beta", "beta", "x"),
    ],
    "Growth": [
        ("Revenue growth (last FY)", "annualRevenueGrowth", "fraction"),
        ("Revenue growth (qtr YoY)", "revenueGrowth", "fraction"),
        ("Earnings growth (qtr YoY)", "earningsGrowth", "fraction"),
    ],
}

# Multiples that mean nothing when the denominator (earnings, EBITDA, growth) is negative.
_LOSS_MULTIPLES = {"trailingPE", "forwardPE", "pegRatio", "enterpriseToEbitda"}

# Banks and insurers fund themselves with deposits and policy reserves, so enterprise value,
# gross margin, liquidity ratios and debt/equity don't describe them.
_NOT_FOR_FINANCIALS = {"enterpriseToRevenue", "enterpriseToEbitda", "grossMargins",
                       "currentRatio", "quickRatio", "debtToEquity", "fcfYield"}

_KIND_NOTES = {
    "financial": "Banks and insurers are judged mainly on price/book and return on equity. Their debt is "
                 "part of the business (deposits, policy reserves), operating cash flow swings with lending, "
                 "and enterprise value, gross margin and liquidity ratios don't apply.",
    "reit": "REIT earnings include property revaluations and depreciation, so P/E is less meaningful. "
            "Price/book (close to price/NAV), dividend yield, payout and gearing matter more.",
}

_STATEMENT_ROWS = {
    "income": ["Total Revenue", "Gross Profit", "Operating Income", "EBITDA", "Net Income", "Diluted EPS"],
    "balance": ["Total Assets", "Total Liabilities Net Minority Interest", "Stockholders Equity",
                "Current Assets", "Current Liabilities", "Cash And Cash Equivalents", "Total Debt"],
    "cashflow": ["Operating Cash Flow", "Capital Expenditure", "Free Cash Flow",
                 "Repurchase Of Capital Stock", "Cash Dividends Paid"],
}


def _statement(frame: pd.DataFrame | None, kind: str) -> dict:
    if frame is None or frame.empty:
        return {"years": [], "rows": []}
    preferred = [r for r in _STATEMENT_ROWS[kind] if r in frame.index]
    shown = frame.loc[preferred] if preferred else frame.iloc[:8]
    # Yahoo often pads an extra year that is empty apart from a stray line or two.
    frame = frame.iloc[:, :5].loc[:, shown.iloc[:, :5].notna().sum() >= max(2, len(shown) // 2)]
    years = [pd.Timestamp(c).strftime("%Y") for c in frame.columns]
    rows = []
    for label in preferred or list(frame.index[:8]):
        values = [num(v) for v in frame.loc[label].tolist()]
        rows.append({"label": label, "values": values, "growth": _growth(values), "cagr": _cagr(values)})
    return {"years": years, "rows": rows}


def _growth(values: list[float | None]) -> list[float | None]:
    """Year-on-year change for each column (newest first). Sign changes have no meaningful
    percentage; for two negatives (e.g. capital spending) it is the change in size."""
    out = []
    for cur, prev in zip(values, values[1:] + [None]):
        same_sign = cur is not None and prev is not None and prev != 0 and (cur > 0) == (prev > 0)
        out.append(cur / prev - 1 if same_sign else None)
    return out


def _cagr(values: list[float | None]) -> float | None:
    known = [(i, v) for i, v in enumerate(values) if v is not None]
    if len(known) < 3:
        return None
    (first_i, newest), (last_i, oldest) = known[0], known[-1]
    if newest <= 0 or oldest <= 0:
        return None
    return (newest / oldest) ** (1 / (last_i - first_i)) - 1


def _kind(data: dict) -> str:
    industry = data.get("industry") or ""
    if industry.startswith(("Banks", "Insurance")):
        return "financial"
    if industry.startswith("REIT"):
        return "reit"
    return "general"


def _annual_growth(income: pd.DataFrame | None) -> float | None:
    if income is None or "Total Revenue" not in income.index:
        return None
    revenue = income.loc["Total Revenue"].dropna()
    if len(revenue) < 2 or revenue.iloc[1] <= 0:
        return None
    return num(revenue.iloc[0] / revenue.iloc[1] - 1)


def _ratio(label: str, key: str, unit: str, data: dict, kind: str) -> dict:
    value, note = num(data.get(key)), None
    if kind == "financial" and key in _NOT_FOR_FINANCIALS:
        value, note = None, "n/a for banks & insurers"
    elif key in _LOSS_MULTIPLES and value is not None and value <= 0:
        value, note = None, "n/m: negative"
    elif key == "trailingPE" and value is None and (num(data.get("trailingEps")) or 0) < 0:
        note = "n/m: loss-making"
    elif key == "returnOnEquity" and kind == "general" and value is not None:
        roa = num(data.get("returnOnAssets"))
        # Equity under a fifth of assets (from buybacks or borrowing) inflates ROE; ROA compares better.
        if roa and roa > 0 and value / roa > 5:
            note = "Inflated by low equity"
    return {"key": key, "label": label, "value": value, "unit": unit, "note": note}


def _latest(frame: pd.DataFrame | None, *rows: str) -> float | None:
    for row in rows:
        if frame is not None and row in frame.index:
            value = num(frame.loc[row].dropna().iloc[0]) if frame.loc[row].notna().any() else None
            if value is not None:
                return value
    return None


def _valuation(data: dict, stmts: dict) -> dict:
    """Ratios that divide market value by statement figures. Yahoo mixes currencies for ADRs
    (TSM's USD market cap over TWD book value), so convert the market cap to the reporting
    currency and recompute them. Also adds free-cash-flow yield."""
    cap = num(data.get("marketCap"))
    trading, reporting = data.get("currency"), data.get("financialCurrency") or data.get("currency")
    keys = ("priceToBook", "priceToSalesTrailing12Months", "enterpriseToRevenue", "enterpriseToEbitda", "enterpriseValue")
    if not cap:
        return {**data, "fcfYield": None}
    rate = 1.0 if trading == reporting else market.fx_rate(trading, reporting)
    if rate is None:  # can't convert, and Yahoo's own figures would be wrong
        return {**data, **dict.fromkeys(keys), "fcfYield": None}
    cap_reported = cap * rate
    out = {**data, "fcfYield": _div(num(data.get("freeCashflow")), cap_reported)}
    if trading != reporting:
        bal = stmts.get("balance")
        debt = _latest(bal, "Total Debt") or 0.0
        cash = _latest(bal, "Cash Cash Equivalents And Short Term Investments", "Cash And Cash Equivalents") or 0.0
        ev = cap_reported + debt - cash
        revenue, ebitda = num(data.get("totalRevenue")), num(data.get("ebitda"))
        out.update({
            "priceToBook": _div(cap_reported, _latest(bal, "Stockholders Equity")),
            "priceToSalesTrailing12Months": _div(cap_reported, revenue),
            "enterpriseToRevenue": _div(ev, revenue),
            "enterpriseToEbitda": _div(ev, ebitda),
            "enterpriseValue": ev / rate,  # back in the trading currency, next to market cap
        })
    return out


def _div(a: float | None, b: float | None) -> float | None:
    return None if a is None or not b else a / b


def _date(epoch) -> str | None:
    return pd.Timestamp(epoch, unit="s").strftime("%Y-%m-%d") if isinstance(epoch, (int, float)) else None


def _positive(value) -> float | None:
    value = num(value)
    return value if value is not None and value > 0 else None


def analyze(symbol: str) -> dict | None:
    data = market.info(symbol)
    if not data:
        return None
    stmts = market.statements(symbol) or {}
    kind = _kind(data)
    data = {**_valuation(data, stmts), "annualRevenueGrowth": _annual_growth(stmts.get("income"))}

    ratios = {
        group: [_ratio(label, key, unit, data, kind) for label, key, unit in items]
        for group, items in RATIO_GROUPS.items()
    }
    income = stmts.get("income")
    trading, reporting = data.get("currency"), data.get("financialCurrency") or data.get("currency")
    fx = 1.0 if trading == reporting else market.fx_rate(trading, reporting)
    history = fundamental_history.build(
        stmts, market.raw_closes(symbol),
        {r["key"]: r["value"] for group in ratios.values() for r in group},
        num(data.get("marketCap")), fx, kind,
    )

    current = num(data.get("currentPrice") or data.get("regularMarketPrice"))
    target = num(data.get("targetMeanPrice"))
    return {
        "symbol": symbol,
        "profile": {
            "name": data.get("longName") or data.get("shortName") or symbol,
            "sector": data.get("sector"),
            "industry": data.get("industry"),
            "country": data.get("country"),
            "website": data.get("website"),
            "employees": data.get("fullTimeEmployees"),
            "summary": data.get("longBusinessSummary"),
            "currency": data.get("currency", "USD"),
            # The statements are in the reporting currency, which differs for ADRs (TSM reports in TWD).
            "financial_currency": data.get("financialCurrency") or data.get("currency", "USD"),
            "kind": kind,
            "kind_note": _KIND_NOTES.get(kind),
        },
        "as_of": {
            "ratios": _date(data.get("mostRecentQuarter")),
            "statements": pd.Timestamp(income.columns[0]).strftime("%Y-%m-%d")
            if income is not None and not income.empty else None,
        },
        "headline": {
            "price": current,
            "market_cap": num(data.get("marketCap")),
            "enterprise_value": num(data.get("enterpriseValue")),
            "pe": _positive(data.get("trailingPE")),
            "forward_pe": _positive(data.get("forwardPE")),
            "loss_making": (num(data.get("trailingEps")) or 0) < 0,
            "week52_low": num(data.get("fiftyTwoWeekLow")),
            "week52_high": num(data.get("fiftyTwoWeekHigh")),
        },
        "ratios": ratios,
        "analyst": {
            "target_mean": target,
            "target_low": num(data.get("targetLowPrice")),
            "target_high": num(data.get("targetHighPrice")),
            "upside_pct": (target - current) / current * 100 if target and current else None,
            "recommendation_mean": num(data.get("recommendationMean")),
            "recommendation_key": data.get("recommendationKey"),
            "analyst_count": data.get("numberOfAnalystOpinions"),
            # yfinance reports dividendYield already in percent (0.41 == 0.41%).
            "dividend_yield_pct": num(data.get("dividendYield")),
            "payout_ratio": num(data.get("payoutRatio")),
        },
        "history": history,
        "quality": quality.quality(stmts, kind),
        "risk": quality.risk(stmts, kind),
        "earnings": quality.earnings(market.earnings(symbol), data.get("earningsTimestampStart") or data.get("earningsTimestamp")),
        "statements": {k: _statement(stmts.get(k), k) for k in _STATEMENT_ROWS},
    }
