"""Market backdrop: rates, volatility, credit, breadth and sector leadership.

These describe the market a call is made in; none of them is a timing signal on its own. Each reading
says which way it leans (supportive, neutral or a headwind for stocks) by a stated rule of thumb.
"""

from concurrent.futures import ThreadPoolExecutor

import pandas as pd

from . import market
from .utils import num, ttl_cache

SECTORS = {
    "XLK": "Technology", "XLC": "Communication Services", "XLY": "Consumer Discretionary", "XLP": "Consumer Staples",
    "XLF": "Financials", "XLV": "Health Care", "XLI": "Industrials", "XLE": "Energy", "XLU": "Utilities",
    "XLRE": "Real Estate", "XLB": "Materials",
}
EXTRA = {"SMH": "Semiconductors"}
TICKERS = ["^TNX", "^IRX", "^VIX", "SPY", "HYG", "IEF", *SECTORS, *EXTRA]


def _ret(close: pd.Series, days: int) -> float | None:
    return num(close.iloc[-1] / close.iloc[-1 - days] - 1) if len(close) > days else None


@ttl_cache(1800)
def context() -> dict | None:
    with ThreadPoolExecutor(max_workers=8) as pool:
        data = dict(zip(TICKERS, pool.map(lambda s: market.closes(s, "2y"), TICKERS)))
    spy = data.get("SPY")
    if spy is None:
        return None
    readings = []

    tnx, irx = data.get("^TNX"), data.get("^IRX")
    if tnx is not None:
        ten = float(tnx.iloc[-1])
        change = num(ten - tnx.iloc[-22]) if len(tnx) > 22 else None
        readings.append({
            "key": "ten_year", "label": "10-year Treasury yield", "value": ten, "unit": "%",
            "detail": None if change is None else f"{change * 100:+.0f} bp over a month",
            "lean": "headwind" if change is not None and change > 0.3 else "supportive" if change is not None and change < -0.3 else "neutral",
            "rule": "A rise of more than 30 bp in a month has tended to weigh on long-duration (growth) stocks.",
        })
    if tnx is not None and irx is not None:
        spread = float(tnx.iloc[-1] - irx.iloc[-1])
        readings.append({
            "key": "curve", "label": "Yield curve (10y − 3m)", "value": spread, "unit": "pp",
            "detail": "inverted" if spread < 0 else "upward sloping",
            "lean": "headwind" if spread < 0 else "neutral",
            "rule": "An inverted curve has preceded most US recessions, often by a year or more; it says little about timing.",
        })

    vix = data.get("^VIX")
    if vix is not None:
        level = float(vix.iloc[-1])
        pctile = float((vix.tail(252) < level).mean() * 100)
        readings.append({
            "key": "vix", "label": "VIX (expected S&P 500 volatility)", "value": level, "unit": "",
            "detail": f"higher than {pctile:.0f}% of the past year",
            "lean": "headwind" if level > 25 else "supportive" if level < 15 else "neutral",
            "rule": "Below 15 is calm, above 25 stressed. High readings mean wide swings both ways.",
        })

    trend = float(spy.iloc[-1] / spy.tail(200).mean() - 1)
    readings.append({
        "key": "trend", "label": "S&P 500 vs its 200-day average", "value": trend * 100, "unit": "%",
        "detail": "above" if trend > 0 else "below",
        "lean": "supportive" if trend > 0 else "headwind",
        "rule": "Markets below their 200-day average have had larger drawdowns and higher volatility (Faber 2007).",
    })

    hyg, ief = data.get("HYG"), data.get("IEF")
    if hyg is not None and ief is not None:
        ratio = (hyg / ief).dropna()
        change = _ret(ratio, 63)
        if change is not None:
            readings.append({
                "key": "credit", "label": "High-yield vs Treasury bonds (3 months)", "value": change * 100, "unit": "%",
                "detail": "credit spreads narrowing" if change > 0 else "credit spreads widening",
                "lean": "headwind" if change < -0.02 else "supportive" if change > 0.01 else "neutral",
                "rule": "Junk bonds lagging Treasuries means lenders want more for risk, which has tended to lead stock weakness.",
            })

    above = [s for s in SECTORS if data.get(s) is not None and len(data[s]) >= 200 and data[s].iloc[-1] > data[s].tail(200).mean()]
    counted = [s for s in SECTORS if data.get(s) is not None and len(data[s]) >= 200]
    if counted:
        share = len(above) / len(counted) * 100
        readings.append({
            "key": "breadth", "label": "Sectors above their 200-day average", "value": share, "unit": "%",
            "detail": f"{len(above)} of {len(counted)}",
            "lean": "supportive" if share >= 70 else "headwind" if share <= 30 else "neutral",
            "rule": "Broad participation is healthier than a rally carried by one or two sectors.",
        })

    spy3 = _ret(spy, 63)
    leaders = []
    for sym, name in {**SECTORS, **EXTRA}.items():
        close = data.get(sym)
        r3, r12 = (_ret(close, 63), _ret(close, 252)) if close is not None else (None, None)
        if r3 is not None:
            leaders.append({"symbol": sym, "name": name, "return_3m": r3 * 100, "return_12m": None if r12 is None else r12 * 100,
                            "vs_spy_3m": None if spy3 is None else (r3 - spy3) * 100})
    leaders.sort(key=lambda x: -(x["vs_spy_3m"] or 0))

    leans = [r["lean"] for r in readings]
    score = leans.count("supportive") - leans.count("headwind")
    regime = "risk-on" if score >= 2 else "risk-off" if score <= -2 else "mixed"
    return {
        "as_of": spy.index[-1].date().isoformat(),
        "regime": regime,
        "supportive": leans.count("supportive"),
        "headwinds": leans.count("headwind"),
        "readings": readings,
        "sectors": leaders,
        "spy_3m": None if spy3 is None else spy3 * 100,
        "spy_12m": None if _ret(spy, 252) is None else _ret(spy, 252) * 100,
    }


def prompt_lines(ctx: dict | None, sector: str | None = None) -> list[str]:
    """The backdrop as prompt lines for the assessment."""
    if not ctx:
        return []
    lines = [f"MARKET BACKDROP (as of {ctx['as_of']}; describes conditions, not a timing signal)",
             f"- Overall: {ctx['regime']} ({ctx['supportive']} readings supportive, {ctx['headwinds']} headwinds)"]
    for r in ctx["readings"]:
        lines.append(f"- {r['label']}: {r['value']:.2f}{r['unit']} ({r['detail']}; {r['lean']})")
    names = {"Technology": "Technology", "Communication Services": "Communication Services", "Consumer Cyclical": "Consumer Discretionary",
             "Consumer Defensive": "Consumer Staples", "Financial Services": "Financials", "Healthcare": "Health Care",
             "Industrials": "Industrials", "Energy": "Energy", "Utilities": "Utilities", "Real Estate": "Real Estate",
             "Basic Materials": "Materials"}
    mine = next((x for x in ctx["sectors"] if x["name"] == names.get(sector or "")), None)
    if mine and mine["vs_spy_3m"] is not None:
        lines.append(f"- This stock's sector ({mine['name']}, {mine['symbol']}) {mine['return_3m']:+.1f}% over 3 months, "
                     f"{mine['vs_spy_3m']:+.1f} pp vs the S&P 500")
    return lines

