"""Your plan: target weights and the trades that restore them, a watchlist, a thesis for each holding
(why you own it, what would make you sell, when to review it), alert rules, and the earnings calendar.

``status`` checks everything against today's prices and returns what needs attention. Some checks
need no rule: an earnings report within a week, a review date that has passed, and a holding that has
drifted from its target by more than the band.
"""

import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import date

from config import normalize_symbol

from . import market, quality
from .portfolio import metrics
from .storage import load_history, load_plan, save_plan, stamp
from .utils import num

# Rule kinds: label, and whether ``value`` is a price, a percentage or a number of days.
ALERT_KINDS = {
    "price_above": ("Price rises above", "price"),
    "price_below": ("Price falls below", "price"),
    "below_cost": ("Falls this far below your average cost", "pct"),
    "weight_above": ("Weight in the portfolio above", "pct"),
    "drawdown": ("Falls this far below its 52-week high", "pct"),
    "estimate_cut": ("This year's EPS estimate cut by more than (90 days)", "pct"),
}

EARNINGS_DAYS = 7


def _clean_symbol(symbol: str) -> str:
    return normalize_symbol(symbol)


# ── Edits ────────────────────────────────────────────────────────────────────

def set_targets(username: str, targets: dict[str, float], band: float | None) -> dict:
    plan = load_plan(username)
    plan["targets"] = {_clean_symbol(k): float(v) for k, v in targets.items() if v is not None and float(v) > 0}
    if band is not None:
        plan["band"] = float(band)
    return save_plan(username, plan)


def add_watch(username: str, symbol: str) -> dict:
    plan = load_plan(username)
    sym = _clean_symbol(symbol)
    if sym not in plan["watchlist"]:
        plan["watchlist"].append(sym)
    return save_plan(username, plan)


def remove_watch(username: str, symbol: str) -> dict:
    plan = load_plan(username)
    plan["watchlist"] = [s for s in plan["watchlist"] if s != _clean_symbol(symbol)]
    return save_plan(username, plan)


def set_thesis(username: str, symbol: str, thesis: str, sell_if: list[str], review_date: str | None) -> dict:
    plan = load_plan(username)
    sym = _clean_symbol(symbol)
    prior = plan["journal"].get(sym, {})
    plan["journal"][sym] = {
        "thesis": thesis.strip(),
        "sell_if": [c.strip() for c in sell_if if c and c.strip()],
        "review_date": review_date or None,
        "created": prior.get("created") or stamp(),
        "updated": stamp(),
    }
    return save_plan(username, plan)


def delete_thesis(username: str, symbol: str) -> dict:
    plan = load_plan(username)
    plan["journal"].pop(_clean_symbol(symbol), None)
    return save_plan(username, plan)


def add_alert(username: str, symbol: str, kind: str, value: float, note: str | None = None) -> dict:
    if kind not in ALERT_KINDS:
        raise ValueError(f"kind must be one of {', '.join(ALERT_KINDS)}")
    plan = load_plan(username)
    plan["alerts"].append({"id": uuid.uuid4().hex[:12], "symbol": _clean_symbol(symbol), "kind": kind,
                           "value": float(value), "note": (note or "").strip() or None, "created": stamp()})
    return save_plan(username, plan)


def delete_alert(username: str, alert_id: str) -> dict:
    plan = load_plan(username)
    plan["alerts"] = [a for a in plan["alerts"] if a["id"] != alert_id]
    return save_plan(username, plan)


# ── Status ───────────────────────────────────────────────────────────────────

def _quote(symbol: str) -> dict:
    """Price, 52-week high, next earnings date and this year's EPS estimate change, from cached data."""
    info = market.info(symbol) or {}
    price = market.price(symbol) or num(info.get("currentPrice") or info.get("regularMarketPrice"))
    earn = quality.earnings(market.earnings(symbol), info.get("earningsTimestampStart") or info.get("earningsTimestamp"))
    year = next((e for e in earn["estimates"] if e["period"] == "0y"), None)
    high = num(info.get("fiftyTwoWeekHigh"))
    return {
        "symbol": symbol,
        "name": info.get("shortName") or info.get("longName") or symbol,
        "currency": info.get("currency") or "USD",
        "price": price,
        "change_pct": num(info.get("regularMarketChangePercent")),
        "high_52w": high,
        "from_high": None if not price or not high else (price / high - 1) * 100,
        "next_earnings": earn["next_date"],
        "estimate_90d": None if not year else year["change_90d"],
        "forward_pe": num(info.get("forwardPE")),
        "target_mean": num(info.get("targetMeanPrice")),
        "recommendation": info.get("recommendationKey"),
    }


def _days_until(day: str | None) -> int | None:
    return None if not day else (date.fromisoformat(day) - date.today()).days


def status(username: str, base: str) -> dict:
    plan = load_plan(username)
    m = metrics(username, base)
    positions: dict[str, dict] = {}
    for r in m["rows"]:
        p = positions.setdefault(r["symbol"], {"symbol": r["symbol"], "quantity": 0.0, "invested": 0.0, "value": 0.0,
                                                "value_base": 0.0, "currency": r["currency"], "price": r["current_price"]})
        p["quantity"] += r["quantity"]
        p["invested"] += r["invested"]
        p["value"] += r["value"]
        p["value_base"] += r["value_base"]
    total = m["total_value"]
    for p in positions.values():
        p["weight"] = p["value_base"] / total * 100 if total else 0.0
        p["avg_cost"] = p["invested"] / p["quantity"] if p["quantity"] else None

    symbols = sorted(set(positions) | set(plan["watchlist"]) | {a["symbol"] for a in plan["alerts"]} | set(plan["targets"]))
    with ThreadPoolExecutor(max_workers=8) as pool:
        quotes = dict(zip(symbols, pool.map(_quote, symbols)))

    last_call: dict[str, dict] = {}
    for h in load_history(username):
        if h["symbol"] in quotes and (h["symbol"] not in last_call or h["timestamp"] > last_call[h["symbol"]]["timestamp"]):
            last_call[h["symbol"]] = {"timestamp": h["timestamp"], "recommendation": h.get("recommendation"),
                                      "confidence": h.get("confidence"), "source": h.get("source", "manual")}

    triggered = []

    def hit(kind: str, symbol: str | None, message: str, severity: str = "warning", rule: str | None = None) -> None:
        triggered.append({"kind": kind, "symbol": symbol, "message": message, "severity": severity, "rule": rule})

    for a in plan["alerts"]:
        q, p = quotes.get(a["symbol"], {}), positions.get(a["symbol"])
        price, v, sym = q.get("price"), a["value"], a["symbol"]
        if a["kind"] == "price_above" and price is not None and price > v:
            hit("rule", sym, f"{sym} is {price:,.2f}, above your {v:,.2f} alert", rule=a["id"])
        elif a["kind"] == "price_below" and price is not None and price < v:
            hit("rule", sym, f"{sym} is {price:,.2f}, below your {v:,.2f} alert", rule=a["id"])
        elif a["kind"] == "below_cost" and p and p["avg_cost"] and price is not None and price < p["avg_cost"] * (1 - v / 100):
            hit("rule", sym, f"{sym} is {(1 - price / p['avg_cost']) * 100:.0f}% below your average cost "
                             f"({p['avg_cost']:,.2f})", rule=a["id"])
        elif a["kind"] == "weight_above" and p and p["weight"] > v:
            hit("rule", sym, f"{sym} is {p['weight']:.1f}% of the portfolio, above your {v:g}% limit", rule=a["id"])
        elif a["kind"] == "drawdown" and q.get("from_high") is not None and q["from_high"] < -v:
            hit("rule", sym, f"{sym} is {-q['from_high']:.0f}% below its 52-week high", rule=a["id"])
        elif a["kind"] == "estimate_cut" and q.get("estimate_90d") is not None and q["estimate_90d"] < -v:
            hit("rule", sym, f"Analysts have cut {sym}'s EPS estimate for this year by {-q['estimate_90d']:.1f}% in 90 days",
                rule=a["id"])

    # Checks that need no rule.
    for sym, q in quotes.items():
        days = _days_until(q.get("next_earnings"))
        if days is not None and 0 <= days <= EARNINGS_DAYS and (sym in positions or sym in plan["watchlist"]):
            hit("earnings", sym, f"{sym} reports earnings {'today' if days == 0 else f'in {days} day' + ('s' if days != 1 else '')} "
                                 f"({q['next_earnings']})", severity="info")
    for sym, j in plan["journal"].items():
        days = _days_until(j.get("review_date"))
        if days is not None and days <= 0 and sym in positions:
            hit("review", sym, f"Your review of {sym} was due {j['review_date']}: check the thesis and the sell conditions",
                severity="info")

    band = plan["band"]
    targeted = sum(plan["targets"].values())
    rebalance = []
    for sym in sorted(set(positions) | set(plan["targets"]), key=lambda s: -(positions.get(s, {}).get("value_base") or 0)):
        p, q = positions.get(sym), quotes.get(sym, {})
        target = plan["targets"].get(sym)
        weight = p["weight"] if p else 0.0
        row = {"symbol": sym, "weight": weight, "target": target, "value": p["value_base"] if p else 0.0,
               "drift": None, "trade": None, "shares": None, "price": q.get("price"), "currency": (p or q).get("currency", "USD")}
        if target is not None and total:
            row["drift"] = weight - target
            row["trade"] = target / 100 * total - row["value"]
            price = q.get("price")
            if price:
                row["shares"] = row["trade"] / market.convert(price, row["currency"], base)
            if abs(row["drift"]) > band:
                hit("drift", sym, f"{sym} is {weight:.1f}% against a {target:g}% target: "
                                  f"{'sell' if row['drift'] > 0 else 'buy'} about {abs(row['trade']):,.0f} {base} to rebalance",
                    severity="info")
        rebalance.append(row)

    calendar = sorted(({"symbol": s, "date": q["next_earnings"], "days": _days_until(q["next_earnings"]),
                        "held": s in positions, "watching": s in plan["watchlist"]}
                       for s, q in quotes.items() if q.get("next_earnings") and (s in positions or s in plan["watchlist"])),
                      key=lambda x: x["date"])

    watch = [{**quotes[s], "last_call": last_call.get(s), "held": s in positions, "thesis": s in plan["journal"]}
             for s in plan["watchlist"] if s in quotes]
    holdings = [{**p, "quote": quotes.get(s), "thesis": plan["journal"].get(s), "last_call": last_call.get(s),
                 "alerts": [a for a in plan["alerts"] if a["symbol"] == s]} for s, p in positions.items()]
    holdings.sort(key=lambda x: -x["value_base"])

    order = {"warning": 0, "info": 1}
    triggered.sort(key=lambda t: order.get(t["severity"], 2))
    return {
        "base_currency": base,
        "total_value": total,
        "band": band,
        "targeted": targeted,
        "triggered": triggered,
        "rebalance": rebalance,
        "calendar": calendar,
        "watchlist": watch,
        "holdings": holdings,
        "alerts": [{**a, "label": ALERT_KINDS[a["kind"]][0], "unit": ALERT_KINDS[a["kind"]][1]} for a in plan["alerts"]],
        "kinds": {k: {"label": v[0], "unit": v[1]} for k, v in ALERT_KINDS.items()},
        "as_of": stamp(),
        "review_soon": [s for s, j in plan["journal"].items()
                        if (d := _days_until(j.get("review_date"))) is not None and 0 < d <= 14],
    }


def digest(username: str, base: str) -> str | None:
    """Plain-text summary of what needs attention, for email; None when nothing does."""
    s = status(username, base)
    if not s["triggered"]:
        return None
    lines = [f"{len(s['triggered'])} thing{'s' if len(s['triggered']) != 1 else ''} in your portfolio need attention:", ""]
    lines += [f"- {t['message']}" for t in s["triggered"]]
    return "\n".join(lines)
