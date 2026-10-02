"""Fundamental analysis: profile, ratios, statements and analyst view."""

import pandas as pd

from . import market
from .utils import num

# Display name -> (yfinance info key, unit). "fraction" values are 0.25 == 25%.
RATIO_GROUPS = {
    "Valuation": [
        ("P/E", "trailingPE", "x"),
        ("Forward P/E", "forwardPE", "x"),
        ("PEG", "pegRatio", "x"),
        ("Price / Book", "priceToBook", "x"),
        ("Price / Sales", "priceToSalesTrailing12Months", "x"),
        ("EV / Revenue", "enterpriseToRevenue", "x"),
        ("EV / EBITDA", "enterpriseToEbitda", "x"),
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
        ("Revenue Growth", "revenueGrowth", "fraction"),
        ("Earnings Growth", "earningsGrowth", "fraction"),
    ],
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
    frame = frame.iloc[:, :5]
    years = [pd.Timestamp(c).strftime("%Y") for c in frame.columns]
    preferred = [r for r in _STATEMENT_ROWS[kind] if r in frame.index]
    rows = []
    for label in preferred or list(frame.index[:8]):
        rows.append({"label": label, "values": [num(v) for v in frame.loc[label].tolist()]})
    return {"years": years, "rows": rows}


def analyze(symbol: str) -> dict | None:
    data = market.info(symbol)
    if not data:
        return None
    stmts = market.statements(symbol) or {}

    ratios = {
        group: [
            {"label": label, "value": num(data.get(key)), "unit": unit}
            for label, key, unit in items
        ]
        for group, items in RATIO_GROUPS.items()
    }

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
        },
        "headline": {
            "price": current,
            "market_cap": num(data.get("marketCap")),
            "enterprise_value": num(data.get("enterpriseValue")),
            "pe": num(data.get("trailingPE")),
            "forward_pe": num(data.get("forwardPE")),
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
        "statements": {kind: _statement(stmts.get(kind), kind) for kind in _STATEMENT_ROWS},
    }
