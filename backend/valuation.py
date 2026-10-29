"""Valuation anchors: how the company compares with its peers, and what growth today's price assumes.

- **Peers** come from Finnhub's same-industry list (US listings), falling back to the stocks you hold
  or watch in the same industry. Each multiple is set against the peer median and ranked.
- **Reverse DCF** solves for the free-cash-flow growth over the next ten years that, with growth then
  slowing to the long-run rate and a CAPM discount rate, makes the cash flows worth today's enterprise
  value. Set it against what the company has grown in the past: a price that needs growth well above
  its record is priced for a lot to go right.
- **Yields** set the earnings, free-cash-flow and shareholder yields beside the 10-year Treasury yield.
"""

from concurrent.futures import ThreadPoolExecutor

import numpy as np
from scipy.optimize import brentq

from . import fundamentals, market
from .storage import load_holdings, load_plan
from .utils import num, ttl_cache

MAX_PEERS = 8
EQUITY_PREMIUM = 0.05      # long-run US equity risk premium
TERMINAL_GROWTH = 0.025    # long-run nominal growth after year ten
YEARS = 10
DISCOUNT_BOUNDS = (0.06, 0.14)

# (key, label, unit, better). "lower" multiples are cheaper; "higher" profitability or growth is better.
PEER_METRICS = [
    ("trailingPE", "P/E", "x", "lower"),
    ("forwardPE", "Forward P/E", "x", "lower"),
    ("pegRatio", "PEG", "x", "lower"),
    ("priceToSalesTrailing12Months", "Price / Sales", "x", "lower"),
    ("enterpriseToEbitda", "EV / EBITDA", "x", "lower"),
    ("grossMargins", "Gross margin", "fraction", "higher"),
    ("operatingMargins", "Operating margin", "fraction", "higher"),
    ("revenueGrowth", "Revenue growth (qtr YoY)", "fraction", "higher"),
    ("returnOnEquity", "Return on equity", "fraction", "higher"),
]
_MULTIPLES = {"trailingPE", "forwardPE", "pegRatio", "priceToSalesTrailing12Months", "enterpriseToEbitda"}
# Yahoo divides a USD market cap by local-currency sales for some ADRs, so these are unusable there.
_CURRENCY_MIXED = {"priceToSalesTrailing12Months", "enterpriseToEbitda"}


def _value(info: dict, key: str) -> float | None:
    v = num(info.get(key))
    if v is None:
        return None
    if key in _MULTIPLES and v <= 0:
        return None  # negative earnings or EBITDA: not meaningful
    if key == "grossMargins" and v <= 0:
        return None  # banks and insurers report no gross profit
    if key in _CURRENCY_MIXED and (info.get("financialCurrency") or info.get("currency")) != info.get("currency"):
        return None
    return v


def _fallback_peers(symbol: str, industry: str | None, username: str) -> list[str]:
    if not industry:
        return []
    pool = {h["Symbol"] for h in load_holdings(username)} | set(load_plan(username).get("watchlist", []))
    pool.discard(symbol)
    infos = {s: market.info(s) for s in pool}
    return [s for s, i in infos.items() if i and i.get("industry") == industry]


def peers(symbol: str, username: str) -> dict:
    me = market.info(symbol) or {}
    found = market.peers(symbol)
    source = "finnhub" if found else "portfolio"
    candidates = (found or _fallback_peers(symbol, me.get("industry"), username))[:MAX_PEERS * 2]
    with ThreadPoolExecutor(max_workers=8) as pool:
        infos = dict(zip(candidates, pool.map(market.info, candidates)))
    # Another listing of the same company (TSM's 2330.TW) isn't a peer.
    mine = me.get("longName")
    names = [s for s in candidates if infos.get(s) and infos[s].get("quoteType") == "EQUITY"
             and not (mine and infos[s].get("longName") == mine)][:MAX_PEERS]
    if not names and source == "finnhub":
        source, names = "portfolio", _fallback_peers(symbol, me.get("industry"), username)[:MAX_PEERS]
        infos.update({s: market.info(s) for s in names})

    rows = []
    for key, label, unit, better in PEER_METRICS:
        mine = _value(me, key)
        others = [v for v in (_value(infos[s], key) for s in names) if v is not None]
        median = float(np.median(others)) if others else None
        # Share of peers the company beats on this measure (cheaper, or more profitable / faster growing).
        rank = None
        if mine is not None and others:
            beats = sum((mine < v) if better == "lower" else (mine > v) for v in others)
            rank = beats / len(others) * 100
        rows.append({"key": key, "label": label, "unit": unit, "better": better, "value": mine, "median": median,
                     "n": len(others), "rank": rank,
                     "vs_median": None if mine is None or not median else mine / median - 1})
    table = [{"symbol": s, "name": infos[s].get("shortName") or s, "market_cap": num(infos[s].get("marketCap")),
              **{key: _value(infos[s], key) for key, *_ in PEER_METRICS}} for s in names]
    table.sort(key=lambda r: -(r["market_cap"] or 0))
    return {"source": source, "industry": me.get("industry"), "peers": table, "rows": rows,
            "self": {"symbol": symbol, "market_cap": num(me.get("marketCap")), **{key: _value(me, key) for key, *_ in PEER_METRICS}}}


def dcf_value(fcf: float, growth: float, rate: float, terminal: float = TERMINAL_GROWTH, years: int = YEARS) -> float:
    """Present value of free cash flow growing at ``growth`` for ``years`` years, then at ``terminal`` forever.
    Growth fades linearly from ``growth`` to ``terminal`` over the second half of the period."""
    pv, cash = 0.0, fcf
    half = years // 2
    for t in range(1, years + 1):
        g = growth if t <= half else growth + (terminal - growth) * (t - half) / (years - half)
        cash *= 1 + g
        pv += cash / (1 + rate) ** t
    return pv + cash * (1 + terminal) / (rate - terminal) / (1 + rate) ** years


def implied_growth(ev: float, fcf: float, rate: float) -> float | None:
    """Growth for the first five years (fading to the long-run rate by year ten) that prices the company at ``ev``."""
    if fcf <= 0 or ev <= 0 or rate <= TERMINAL_GROWTH:
        return None
    f = lambda g: dcf_value(fcf, g, rate) - ev  # noqa: E731
    lo, hi = -0.5, 1.5
    if f(lo) > 0:
        return lo
    if f(hi) < 0:
        return None
    return brentq(f, lo, hi)


@ttl_cache(3600)
def _ten_year() -> float | None:
    close = market.closes("^TNX", "1mo")
    return None if close is None else float(close.iloc[-1]) / 100


def anchor(symbol: str) -> dict:
    """Reverse DCF and yields from the latest figures."""
    fund = fundamentals.analyze(symbol)
    info = market.info(symbol) or {}
    if fund is None:
        raise LookupError(symbol)
    stmts = market.statements(symbol) or {}
    trading, reporting = info.get("currency"), info.get("financialCurrency") or info.get("currency")
    fx = 1.0 if trading == reporting else (market.fx_rate(trading, reporting) or None)
    cap = num(info.get("marketCap"))
    cap_rep = cap * fx if cap and fx else None
    debt, cash = num(info.get("totalDebt")) or 0.0, num(info.get("totalCash")) or 0.0
    ev = cap_rep + debt - cash if cap_rep else None
    # The cash flow statement's free cash flow; Yahoo's info field is a levered estimate that runs well below it.
    fcf = fundamentals._latest(stmts.get("cashflow"), "Free Cash Flow") or num(info.get("freeCashflow"))
    rf = _ten_year() or 0.045
    beta = num(info.get("beta"))
    raw_rate = rf + (beta if beta is not None else 1.0) * EQUITY_PREMIUM
    rate = min(max(raw_rate, DISCOUNT_BOUNDS[0]), DISCOUNT_BOUNDS[1])
    kind = fund["profile"]["kind"]

    implied, sensitivity, note = None, [], None
    if kind == "financial":
        note = "Free cash flow doesn't describe a bank or insurer, so there's no reverse DCF."
    elif not fcf or fcf <= 0:
        note = "Free cash flow is negative or missing, so no growth rate can justify the price on cash flow alone."
    elif not ev or ev <= 0:
        note = "Enterprise value is unavailable."
    else:
        implied = implied_growth(ev, fcf, rate)
        sensitivity = [{"rate": r * 100, "growth": None if (g := implied_growth(ev, fcf, r)) is None else g * 100}
                       for r in (rate - 0.01, rate, rate + 0.01)]

    def cagr(kind_: str, row: str) -> float | None:
        values = next((r["values"] for r in fund["statements"][kind_]["rows"] if r["label"] == row), None)
        if not values:
            return None
        known = [v for v in values if v is not None]
        if len(known) < 3 or known[0] <= 0 or known[-1] <= 0:
            return None
        return (known[0] / known[-1]) ** (1 / (len(known) - 1)) - 1

    revenue_cagr, fcf_cagr = cagr("income", "Total Revenue"), cagr("cashflow", "Free Cash Flow")
    estimates = {e["period"]: e for e in fund["earnings"]["estimates"]}
    this, nxt = estimates.get("0y"), estimates.get("+1y")
    eps_growth = (nxt["current"] / this["current"] - 1) if this and nxt and this["current"] and this["current"] > 0 and nxt["current"] else None

    # Yields: what each dollar of market value earns now.
    cf = stmts.get("cashflow")
    buybacks = -(fundamentals._latest(cf, "Repurchase Of Capital Stock") or 0.0)
    issued = fundamentals._latest(cf, "Issuance Of Capital Stock") or 0.0
    paid = -(fundamentals._latest(cf, "Cash Dividends Paid") or 0.0)
    pe, fpe = num(info.get("trailingPE")), num(info.get("forwardPE"))
    yields = {
        "earnings": 1 / pe * 100 if pe and pe > 0 else None,
        "forward_earnings": 1 / fpe * 100 if fpe and fpe > 0 else None,
        "fcf": fcf / cap_rep * 100 if fcf and cap_rep else None,
        "dividend": num(info.get("dividendYield")),
        "shareholder": (paid + buybacks - issued) / cap_rep * 100 if cap_rep else None,
        "treasury_10y": rf * 100,
    }
    best = yields["forward_earnings"] if yields["forward_earnings"] is not None else yields["earnings"]
    return {
        "currency": reporting,
        "discount_rate": rate * 100,
        "discount_inputs": {"risk_free": rf * 100, "beta": beta, "premium": EQUITY_PREMIUM * 100,
                            "clamped": abs(raw_rate - rate) > 1e-9},
        "terminal_growth": TERMINAL_GROWTH * 100,
        "fcf": fcf, "enterprise_value": ev,
        "implied_growth": None if implied is None else implied * 100,
        "sensitivity": sensitivity,
        "history": {"revenue_cagr": None if revenue_cagr is None else revenue_cagr * 100,
                    "fcf_cagr": None if fcf_cagr is None else fcf_cagr * 100,
                    "eps_growth_next_year": None if eps_growth is None else eps_growth * 100,
                    "years": len(fund["statements"]["income"]["years"])},
        "yields": yields,
        "yield_gap": None if best is None else best - rf * 100,
        "note": note,
    }


def analyze(symbol: str, username: str) -> dict:
    with ThreadPoolExecutor(max_workers=2) as pool:
        p = pool.submit(peers, symbol, username)
        a = pool.submit(anchor, symbol)
        return {"symbol": symbol, "peers": p.result(), "anchor": a.result()}


def prompt_lines(v: dict | None) -> list[str]:
    """Peers and the reverse DCF as prompt lines for the assessment."""
    if not v:
        return []
    lines = []
    p = v.get("peers")
    if p and p["peers"]:
        parts = []
        for r in p["rows"]:
            if r["value"] is None or r["median"] is None:
                continue
            show = (lambda x: f"{x * 100:.1f}%") if r["unit"] == "fraction" else (lambda x: f"{x:.1f}")
            parts.append(f"{r['label']} {show(r['value'])} vs peer median {show(r['median'])}")
        if parts:
            lines.append(f"- Against {len(p['peers'])} peers in {p['industry'] or 'its industry'} "
                         f"({', '.join(x['symbol'] for x in p['peers'][:6])}): " + "; ".join(parts))
    a = v.get("anchor")
    if a:
        if a["implied_growth"] is not None:
            h = a["history"]
            hist = ", ".join(x for x in (
                None if h["revenue_cagr"] is None else f"revenue {h['revenue_cagr']:+.1f}%/yr",
                None if h["fcf_cagr"] is None else f"free cash flow {h['fcf_cagr']:+.1f}%/yr",
                None if h["eps_growth_next_year"] is None else f"analysts' next-year EPS growth {h['eps_growth_next_year']:+.1f}%",
            ) if x)
            lines.append(f"- Reverse DCF: today's enterprise value implies free cash flow growth of {a['implied_growth']:.1f}% a year "
                         f"for five years, fading to {a['terminal_growth']:.1f}% by year ten (discount rate {a['discount_rate']:.1f}%)"
                         + (f"; past growth: {hist}" if hist else ""))
        elif a["note"]:
            lines.append(f"- Reverse DCF: {a['note']}")
        y = a["yields"]
        if a["yield_gap"] is not None:
            earnings = y["forward_earnings"] if y["forward_earnings"] is not None else y["earnings"]
            fcf = "n/a" if y["fcf"] is None else f"{y['fcf']:.1f}%"
            lines.append(f"- Earnings yield {earnings:.1f}% (forward if available) vs 10-year Treasury "
                         f"{y['treasury_10y']:.2f}%; FCF yield {fcf}")
    return (["", "VALUATION ANCHORS"] + lines) if lines else []
