"""Portfolio risk: how the holdings move together, what drives the risk, how much it could lose, and
what a trade would change.

Everything is computed on daily dividend-adjusted returns converted to the base currency, so currency
moves count as risk the way they do for your money. Statistics use the last year of trading days; the
drawdown uses the last three years with today's weights held constant (rebalanced daily).
"""

from concurrent.futures import ThreadPoolExecutor
from datetime import date

import numpy as np
import pandas as pd

from config import normalize_symbol

from . import market
from .portfolio import metrics
from .utils import num

BENCHMARK = "SPY"
WINDOW = 252          # trading days of returns behind the statistics
DRAWDOWN_DAYS = 756   # three years
MIN_DAYS = 60         # fewer days of history and a holding is left out of the statistics

# Market stress episodes, peak to trough of the S&P 500.
SCENARIOS = [
    ("Q4 2018 selloff", "2018-09-20", "2018-12-24"),
    ("COVID crash", "2020-02-19", "2020-03-23"),
    ("2022 bear market", "2022-01-03", "2022-10-12"),
    ("Aug 2024 yen-carry unwind", "2024-07-16", "2024-08-05"),
    ("Apr 2025 tariff shock", "2025-04-02", "2025-04-08"),
]

# Rules of thumb behind the warnings.
LIMITS = {"position": 20.0, "industry": 30.0, "sector_vs_benchmark": 2.0, "effective_bets": 4.0}


# ── Statistics on a return matrix ────────────────────────────────────────────

def stats(returns: pd.DataFrame, weights: pd.Series, bench: pd.Series) -> dict:
    """Risk of a portfolio with constant ``weights`` (summing to 1) over the rows of ``returns``."""
    R = returns[weights.index].fillna(0.0)
    b = bench.reindex(R.index).fillna(0.0)
    w = weights.to_numpy()
    cov = R.cov().to_numpy() * 252
    var_p = float(w @ cov @ w)
    sigma_p = np.sqrt(var_p) if var_p > 0 else 0.0
    vols = np.sqrt(np.diag(cov))
    rp = R.to_numpy() @ w
    bvar = float(b.var())
    betas = [float(np.cov(R[c], b)[0, 1] / bvar) if bvar else None for c in R.columns]

    # Each holding's share of the portfolio's variance (sums to 1).
    risk_share = (w * (cov @ w)) / var_p if var_p > 0 else np.zeros_like(w)
    corr = R.corr().fillna(0.0)
    off = ~np.eye(len(w), dtype=bool)
    pair_w = np.outer(w, w)[off]
    avg_corr = float((corr.to_numpy()[off] * pair_w).sum() / pair_w.sum()) if pair_w.sum() > 0 else None

    rest = []
    for i, c in enumerate(R.columns):
        others = np.delete(w, i)
        if others.sum() <= 0:
            rest.append(None)
            continue
        ex = R.drop(columns=c).to_numpy() @ (others / others.sum())
        rest.append(num(np.corrcoef(R[c], ex)[0, 1]))

    q05, q01 = np.quantile(rp, 0.05), np.quantile(rp, 0.01)
    dr = float(w @ vols / sigma_p) if sigma_p else None
    return {
        "vol": sigma_p * 100,
        "beta": float(np.cov(rp, b)[0, 1] / bvar) if bvar else None,
        "var95": -q05 * 100,
        "var99": -q01 * 100,
        "cvar95": -rp[rp <= q05].mean() * 100,
        "diversification_ratio": dr,
        # Choueifaty & Coignard: the diversification ratio squared approximates the number of independent bets.
        "effective_bets": dr ** 2 if dr else None,
        "hhi_bets": 1 / float((w ** 2).sum()),
        "avg_corr": avg_corr,
        "bench_vol": float(b.std() * np.sqrt(252) * 100),
        "holdings": {c: {"vol": float(vols[i] * 100), "beta": betas[i], "risk_share": float(risk_share[i] * 100),
                         "corr_to_rest": rest[i]} for i, c in enumerate(R.columns)},
        "corr": corr,
    }


def drawdown(growth: pd.Series) -> dict:
    """Largest fall from a peak, when it ran, and how far below its peak the series is now."""
    peak = growth.cummax()
    dd = growth / peak - 1
    trough = dd.idxmin()
    start = growth.loc[:trough].idxmax()
    return {"max": float(dd.min() * 100), "from": start.date().isoformat(), "to": trough.date().isoformat(),
            "current": float(dd.iloc[-1] * 100), "series": dd}


def scenario_return(prices: pd.Series | None, start: str, end: str) -> float | None:
    """Return over the window, or None when the history doesn't reach back to its start."""
    if prices is None or prices.empty or prices.index[0] > pd.Timestamp(start):
        return None
    a, z = prices.asof(pd.Timestamp(start)), prices.asof(pd.Timestamp(end))
    return None if pd.isna(a) or pd.isna(z) or not a else float(z / a - 1)


# ── Data ─────────────────────────────────────────────────────────────────────

def _in_base(close: pd.Series | None, currency: str, base: str) -> pd.Series | None:
    if close is None or currency == base:
        return close
    rate = market.fx_history(currency, base)
    if rate is None:
        return close * (market.fx_rate(currency, base) or 1.0)
    return close * rate.reindex(close.index.union(rate.index)).ffill().bfill().reindex(close.index)


def _load(symbols: dict[str, str], base: str) -> dict:
    """Prices in the base currency and profiles for ``symbols`` ({symbol: currency}), and the benchmark."""
    names = list(symbols)
    with ThreadPoolExecutor(max_workers=8) as pool:
        closes = dict(zip(names, pool.map(lambda s: market.closes(s, "10y"), names)))
        infos = dict(zip(names, pool.map(market.info, names)))
        funds = dict(zip(names, pool.map(lambda s: market.fund_sectors(s) if (infos.get(s) or {}).get("quoteType") == "ETF" else None, names)))
    bench = market.closes(BENCHMARK, "10y")
    if bench is None:
        raise LookupError("Couldn't fetch S&P 500 (SPY) history. Yahoo Finance may be rate-limiting; try again shortly.")
    return {
        "prices": {s: _in_base(closes[s], symbols[s], base) for s in names},
        "infos": infos,
        "funds": funds,
        "bench": _in_base(bench, "USD", base),
        "bench_sectors": market.fund_sectors(BENCHMARK),
    }


def _profile(sym: str, data: dict) -> dict:
    info = data["infos"].get(sym) or {}
    fund = info.get("quoteType") == "ETF"
    return {
        "name": info.get("longName") or info.get("shortName") or sym,
        "sector": "ETF / Fund" if fund else info.get("sector") or "Unknown",
        "industry": ("Fund: " + (info.get("category") or "diversified")) if fund else info.get("industry") or "Unknown",
        "country": "Fund" if fund else info.get("country") or "Unknown",
        "fund": fund,
    }


def _group(items: list[tuple[str, float]]) -> list[dict]:
    totals: dict[str, float] = {}
    for name, weight in items:
        totals[name] = totals.get(name, 0.0) + weight
    return sorted(({"name": k, "weight": v} for k, v in totals.items()), key=lambda x: -x["weight"])


# ── Analysis ─────────────────────────────────────────────────────────────────

def analyze(values: dict[str, float], currencies: dict[str, str], data: dict, base: str) -> dict:
    """Risk of holding ``values`` (base-currency value by symbol)."""
    total = sum(v for v in values.values() if v > 0)
    held = {s: v for s, v in values.items() if v > 0}
    prices = pd.DataFrame({s: data["prices"][s] for s in held if data["prices"].get(s) is not None})
    bench_px = data["bench"]
    frame = prices.join(bench_px.rename("__bench__"), how="outer").sort_index().ffill(limit=5)
    rets = frame.pct_change(fill_method=None)
    recent = rets.tail(WINDOW)
    usable = [s for s in prices.columns if recent[s].notna().sum() >= MIN_DAYS]
    excluded = sorted(set(held) - set(usable))
    weights_all = pd.Series({s: held[s] / total for s in held}) if total else pd.Series(dtype=float)
    w = weights_all[usable] / weights_all[usable].sum() if usable else pd.Series(dtype=float)

    profiles = {s: _profile(s, data) for s in held}
    out: dict = {"total_value": total, "base_currency": base, "window_days": WINDOW, "excluded": excluded,
                 "as_of": date.today().isoformat()}
    if w.empty:
        return {**out, "portfolio": None, "holdings": [], "correlation": None, "exposure": None, "scenarios": [],
                "drawdown": None, "flags": []}

    s = stats(recent[usable], w, recent["__bench__"])

    # Drawdown of today's weights over three years, and the benchmark's over the same days.
    long = rets.tail(DRAWDOWN_DAYS)
    growth = (1 + long[usable].fillna(0.0) @ w).cumprod()
    bench_growth = (1 + long["__bench__"].fillna(0.0)).cumprod()
    dd, bdd = drawdown(growth), drawdown(bench_growth)
    step = max(1, len(growth) // 160)
    dd_series = [{"date": d.date().isoformat(), "portfolio": float(dd["series"].iloc[i] * 100),
                  "benchmark": float(bdd["series"].iloc[i] * 100)}
                 for i, d in enumerate(growth.index) if i % step == 0 or i == len(growth) - 1]

    holdings = []
    for sym in sorted(held, key=lambda x: -held[x]):
        h = s["holdings"].get(sym, {})
        holdings.append({"symbol": sym, "value": held[sym], "weight": weights_all[sym] * 100, **profiles[sym],
                         "currency": currencies.get(sym, "USD"), "vol": h.get("vol"), "beta": h.get("beta"),
                         "risk_share": h.get("risk_share"), "corr_to_rest": h.get("corr_to_rest"),
                         "history_days": int(recent[sym].notna().sum()) if sym in recent else 0})

    # Funds are looked through to their sector weights where Yahoo has them.
    sector_items = []
    for sym, weight in weights_all.items():
        fund = data["funds"].get(sym)
        if fund:
            sector_items += [(k, weight * 100 * v / sum(fund.values())) for k, v in fund.items()]
        else:
            sector_items.append((profiles[sym]["sector"], weight * 100))
    bench_sectors = {k: v * 100 for k, v in (data["bench_sectors"] or {}).items()}
    sectors = _group(sector_items)
    for row in sectors:
        row["benchmark"] = bench_sectors.get(row["name"])
    for name, bw in bench_sectors.items():
        if not any(r["name"] == name for r in sectors):
            sectors.append({"name": name, "weight": 0.0, "benchmark": bw})

    exposure = {
        "sector": sectors,
        "industry": _group([(profiles[x]["industry"], weights_all[x] * 100) for x in held]),
        "currency": _group([(currencies.get(x, "USD"), weights_all[x] * 100) for x in held]),
        "country": _group([(profiles[x]["country"], weights_all[x] * 100) for x in held]),
    }

    scenarios = []
    for name, start, end in SCENARIOS:
        b = scenario_return(bench_px, start, end)
        if b is None:
            continue
        rows, total_r = [], 0.0
        for sym in held:
            r = scenario_return(data["prices"].get(sym), start, end)
            beta = s["holdings"].get(sym, {}).get("beta")
            estimated = r is None
            if estimated:
                r = (beta if beta is not None else 1.0) * b
            rows.append({"symbol": sym, "return": r * 100, "estimated": estimated})
            total_r += weights_all[sym] * r
        scenarios.append({"name": name, "start": start, "end": end, "benchmark": b * 100, "portfolio": total_r * 100,
                          "loss": total_r * total, "estimated": sum(r["estimated"] for r in rows), "rows": rows})

    flags = []
    for h in holdings:
        if h["weight"] > LIMITS["position"]:
            flags.append({"severity": "warning", "kind": "position",
                          "message": f"{h['symbol']} is {h['weight']:.0f}% of the portfolio (above {LIMITS['position']:.0f}%)"
                                     + (f" and {h['risk_share']:.0f}% of its risk" if h["risk_share"] is not None else "")})
    for row in exposure["industry"]:
        if row["weight"] > LIMITS["industry"] and not row["name"].startswith("Fund"):
            members = [h["symbol"] for h in holdings if h["industry"] == row["name"]]
            flags.append({"severity": "warning", "kind": "industry",
                          "message": f"{row['name']} is {row['weight']:.0f}% of the portfolio ({', '.join(members)})"})
    for row in sectors:
        if row["benchmark"] and row["weight"] > 15 and row["weight"] > LIMITS["sector_vs_benchmark"] * row["benchmark"]:
            flags.append({"severity": "info", "kind": "sector",
                          "message": f"{row['name']} is {row['weight']:.0f}% of the portfolio against {row['benchmark']:.0f}% of the S&P 500"})
    if s["effective_bets"] is not None and s["effective_bets"] < LIMITS["effective_bets"] and len(usable) >= 3:
        flags.append({"severity": "warning", "kind": "bets",
                      "message": f"{len(usable)} holdings behave like about {s['effective_bets']:.1f} independent bets"})
    if s["beta"] is not None and s["beta"] > 1.3:
        flags.append({"severity": "info", "kind": "beta",
                      "message": f"Beta {s['beta']:.2f}: the portfolio has moved about {s['beta']:.1f}× as much as the S&P 500"})

    corr = s["corr"]
    return {
        **out,
        "portfolio": {k: s[k] for k in ("vol", "beta", "var95", "var99", "cvar95", "diversification_ratio",
                                        "effective_bets", "hhi_bets", "avg_corr", "bench_vol")}
                     | {"var95_amount": s["var95"] / 100 * total, "cvar95_amount": s["cvar95"] / 100 * total,
                        "max_drawdown": dd["max"], "drawdown_from": dd["from"], "drawdown_to": dd["to"],
                        "current_drawdown": dd["current"], "bench_max_drawdown": bdd["max"],
                        "holdings_used": len(usable)},
        "holdings": holdings,
        "correlation": {"symbols": list(corr.columns), "matrix": corr.to_numpy().round(3).tolist()},
        "exposure": exposure,
        "scenarios": scenarios,
        "drawdown": dd_series,
        "flags": flags,
    }


def _positions(username: str, base: str) -> tuple[dict[str, float], dict[str, str]]:
    m = metrics(username, base)
    values: dict[str, float] = {}
    currencies: dict[str, str] = {}
    for r in m["rows"]:
        values[r["symbol"]] = values.get(r["symbol"], 0.0) + r["value_base"]
        currencies[r["symbol"]] = r["currency"]
    return values, currencies


def build(username: str, base: str) -> dict:
    values, currencies = _positions(username, base)
    if not values:
        return {"total_value": 0, "base_currency": base, "portfolio": None, "holdings": [], "flags": [], "empty": True}
    return analyze(values, currencies, _load(currencies, base), base)


def what_if(username: str, base: str, trades: list[dict]) -> dict:
    """The portfolio's risk before and after ``trades`` ([{symbol, amount}], amount in the base
    currency: positive buys, negative sells)."""
    values, currencies = _positions(username, base)
    after = dict(values)
    for t in trades:
        sym = normalize_symbol(t["symbol"])
        if sym not in currencies:
            info = market.info(sym)
            if not info:
                raise LookupError(f"Couldn't find {sym}")
            currencies[sym] = info.get("currency") or "USD"
        after[sym] = max(0.0, after.get(sym, 0.0) + float(t["amount"]))
    data = _load(currencies, base)
    before_r = analyze(values, currencies, data, base) if values else None
    after_r = analyze(after, currencies, data, base)

    def summary(r: dict | None) -> dict | None:
        if not r or not r.get("portfolio"):
            return None
        top_industry = r["exposure"]["industry"][0] if r["exposure"]["industry"] else None
        return {**r["portfolio"], "total_value": r["total_value"], "flags": r["flags"],
                "top_industry": top_industry, "holdings": {h["symbol"]: h for h in r["holdings"]},
                "worst_scenario": min(r["scenarios"], key=lambda x: x["portfolio"]) if r["scenarios"] else None}

    traded = [normalize_symbol(t["symbol"]) for t in trades]
    return {"base_currency": base, "trades": [{"symbol": normalize_symbol(t["symbol"]), "amount": float(t["amount"])} for t in trades],
            "symbols": traded, "before": summary(before_r), "after": summary(after_r)}
