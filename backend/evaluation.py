"""Second look at a one-shot AI assessment.

Rules in code pick which skills apply (backend/skills/*/SKILL.md). Each skill has a facts
function that computes the numbers it needs and runs quick rule screens, so Gemini judges
from given facts instead of doing arithmetic. One Gemini call then reviews the recommendation
with the selected skills. The evaluation flags problems and may lower confidence; it never
changes the recommendation itself.
"""

import json
import math
import re
from datetime import date, datetime
from functools import lru_cache
from pathlib import Path
from typing import Callable, Literal

import yaml
from pydantic import BaseModel, Field

from config import GEMINI_AVAILABLE, get_gemini_api_key, is_gemini_api_configured

from . import portfolio, technical, usage
from .assessment import MODEL, THINKING_LEVEL, Assessment
from .storage import update_history

SKILLS_DIR = Path(__file__).parent / "skills"
# Calendar days each time horizon covers when deciding whether an earnings report falls inside it.
HORIZON_DAYS = {"Short-term": 90, "Medium-term": 365, "Long-term": 3 * 365}
RECENT_SIGNAL_DAYS = 30  # a technical signal that fired within this many days counts as current
CONCENTRATED_PCT = 20  # rule-of-thumb share of the portfolio above which adding needs a reason


@lru_cache
def skills() -> dict[str, dict]:
    """Every skill's frontmatter and instructions, keyed by name."""
    out = {}
    for path in sorted(SKILLS_DIR.glob("*/SKILL.md")):
        _, front, body = path.read_text(encoding="utf-8").split("---", 2)
        meta = yaml.safe_load(front)
        out[meta["name"]] = {"name": meta["name"], "description": meta["description"], **meta["metadata"], "body": body.strip()}
    return out


# ── Helpers ──────────────────────────────────────────────────────────────────

def _round(x):
    """Round floats to 4 significant figures so the fact sheets stay short."""
    if isinstance(x, float):
        return float(f"{x:.4g}") if math.isfinite(x) else None
    if isinstance(x, dict):
        return {k: _round(v) for k, v in x.items()}
    if isinstance(x, list):
        return [_round(v) for v in x]
    return x


def _text(ai: dict) -> str:
    """All of the recommendation's prose, lower-cased, for the rule screens."""
    parts = [ai["summary"], ai["position_advice"], *ai["strengths"], *ai["risks"],
             *(f"{s['title']}. {s['content']}" for s in ai["steps"])]
    return "\n".join(parts).lower()


def _sentences(text: str) -> list[str]:
    return re.split(r"(?<=[.!?;])\s+|\n", text)


_NEGATION = re.compile(r"(\bnot\b|n't|\bno longer\b|\bnor\b|\bneither\b|\bwithout\b|\bapproach\w*|\bnear\w*|\btoward\w*)\W*(\w+\W+){0,2}$")


def _asserts(text: str, phrase: str) -> str | None:
    """The first sentence where ``phrase`` appears without a negation or hedge just before it."""
    for sentence in _sentences(text):
        for m in re.finditer(phrase, sentence):
            if not _NEGATION.search(sentence[max(0, m.start() - 30):m.start()]):
                return sentence.strip()
    return None


def _quote(sentence: str) -> str:
    return f'"{sentence[:120]}{"…" if len(sentence) > 120 else ""}"'


def _check(skill: str, check: str, passed: bool, detail: str) -> dict:
    return {"skill": skill, "check": check, "passed": passed, "detail": detail}


def _pct(a: float | None, b: float | None) -> float | None:
    return None if a is None or not b else (a - b) / b * 100


def _days_to(iso: str | None, today: date) -> int | None:
    if not iso:
        return None
    try:
        return (date.fromisoformat(iso[:10]) - today).days
    except ValueError:
        return None


def _adds(ai: dict) -> bool:
    return bool(re.search(r"\b(add|adding|accumulate|increase|buy more|top up|build (a|the|your) position)\b", ai["position_advice"].lower()))


# ── Facts and rule screens for each skill ────────────────────────────────────
# Each returns (facts, checks), or None when the skill doesn't apply.

def _claim_check(ctx: dict, ai: dict, text: str, _: dict) -> tuple[dict, list]:
    t, f = ctx["technical"], ctx["fundamental"]
    sig, p, s = t["signals"], ctx.get("predictive"), ctx.get("sentiment")
    rsi = sig["rsi"]["value"]
    missing = [name for name, v in (("forecast models", p), ("news sentiment", s), ("your position", ctx.get("position"))) if not v]
    facts = {
        "price": t["quote"]["price"],
        "currency": f["profile"].get("currency"),
        "change_today_pct": t["quote"]["change_pct"],
        "rsi_14": {"value": rsi, "state": sig["rsi"]["state"]},
        "macd": {"state": sig["macd"]["state"], "macd": sig["macd"]["macd"], "signal": sig["macd"]["signal"]},
        "bollinger": {"percent_b": sig["bollinger"]["percent_b"], "state": sig["bollinger"]["state"]},
        "sma50": sig["trend"]["sma50"],
        "sma200": sig["trend"]["sma200"],
        "golden_cross": sig["trend"]["golden_cross"],
        "momentum_12_1_pct": None if sig["momentum"]["return_12_1"] is None else sig["momentum"]["return_12_1"] * 100,
        "from_52w_high_pct": None if sig["high_52w"]["distance"] is None else sig["high_52w"]["distance"] * 100,
        "adx": {"value": sig["adx"]["value"], "state": sig["adx"]["state"], "direction": sig["adx"]["direction"]},
        "pe": f["headline"]["pe"], "forward_pe": f["headline"]["forward_pe"], "loss_making": f["headline"]["loss_making"],
        "analysts": {"consensus": f["analyst"].get("recommendation_key"), "target_mean": f["analyst"].get("target_mean"),
                     "upside_pct": f["analyst"].get("upside_pct"), "count": f["analyst"].get("analyst_count")},
        "forecast": p and {"any_model_beat_no_change": p["any_skill"],
                           "models": [{"name": m["name"], "verdict": m["verdict"]} for m in p["models"]]},
        "news_sentiment": s and {"tilt": s["overall"] or "too few headlines", "net_tone": s["index"], "ci_95": s["ci"], "headlines": s["n"]},
        "missing_sections": missing,
    }

    checks = []
    if rsi is not None:
        # 5 points of slack: "overbought" at RSI 68 is loose wording, not a misreading.
        if (said := _asserts(text, r"overbought")) and rsi < 65:
            checks.append(_check("claim-check", "RSI reading", False, f"{_quote(said)} calls the stock overbought, but RSI is {rsi:.0f} (overbought is above 70)."))
        if (said := _asserts(text, r"oversold")) and rsi > 35:
            checks.append(_check("claim-check", "RSI reading", False, f"{_quote(said)} calls the stock oversold, but RSI is {rsi:.0f} (oversold is below 30)."))
    state = sig["macd"]["state"]
    if state:
        opposite = "bullish" if state == "bearish" else "bearish"
        said = next((x for x in _sentences(text) if "macd" in x and _asserts(x, opposite) and not _asserts(x, state)), None)
        if said:
            checks.append(_check("claim-check", "MACD reading", False, f"{_quote(said.strip())} describes MACD as {opposite}; it is {state}."))
    for days in ("50", "200"):
        trend = sig["trend"][f"sma{days}"]
        if trend["value"] is None:
            continue
        wrong = "below" if trend["price_above"] else "above"
        if said := _asserts(text, rf"\b{wrong} (the |its )?{days}[- ]day"):
            checks.append(_check("claim-check", f"{days}-day average", False,
                                 f"{_quote(said)} puts the price {wrong} the {days}-day average ({trend['value']:.2f}); "
                                 f"it is {'above' if trend['price_above'] else 'below'} it, at {ctx['technical']['quote']['price']:.2f}."))
    if p and not p["any_skill"]:
        leaned = [x for x in _sentences(text)
                  if re.search(r"\b(forecast|ml|machine[- ]learning|lightgbm|chronos|arima|ridge|gradient|random forest|predictive)", x)
                  and re.search(r"\b(predict|expect|project|point|suggest|indicat|upside|rise|gain|declin|fall)", x)
                  # The GARCH range is a valid use; sentences that say the models have no edge are fine.
                  and not re.search(r"garch|range|volatil|\bno\b|\bnot\b|n't|without|neutral|lack|fail|insignificant|no-change", x)]
        if leaned:
            checks.append(_check("claim-check", "Forecast reliance", False,
                                 f"{_quote(leaned[0].strip())} uses the forecast models' direction, but none beat the no-change forecast."))
    if not s:
        # Only news-specific wording: "analyst sentiment" or "earnings sentiment" is about other data.
        news = [x for x in _sentences(text) if re.search(r"\bnews\b|headlines?\b|media coverage|press coverage", x)
                and not re.search(r"\b(no|not|n't|without|unavailable|missing|excluded)\b", x)]
        if news:
            checks.append(_check("claim-check", "Missing data",
                                 False, f"{_quote(news[0].strip())} discusses news, which wasn't included in this analysis."))
    if s and s["overall"] not in ("Positive", "Negative") and _asserts(text, r"(positive|bullish|negative|bearish|upbeat|pessimistic) (news |media )?(sentiment|tone|coverage)"):
        checks.append(_check("claim-check", "News tone", False,
                             f"Describes news tone as positive or negative, but its 95% interval includes zero ({s['n']} headlines)."))
    return facts, checks


_AXIS_WORDS = {
    "Valuation": r"valuation|p/e|multiple|expensive|cheap|priced|premium",
    "Growth": r"growth|revenue",
    "Profitability": r"margin|profitab|return on",
    "Momentum": r"momentum|trend|rsi|macd|moving average|\d+-day",
    "Balance sheet": r"debt|balance sheet|leverage|liquidity|altman",
    "Quality": r"piotroski|f-score|quality",
    "Earnings": r"earnings|eps|estimate|surprise",
    "Sentiment": r"sentiment|news|headline",
    "Forecast": r"forecast|model",
}
_BULLISH = {"buy", "strong_buy", "outperform"}
_BEARISH = {"sell", "strong_sell", "underperform"}


def _counter_case(ctx: dict, ai: dict, text: str, _: dict) -> tuple[dict, list]:
    rec, scores = ai["recommendation"], {x["axis"]: x["score"] for x in ctx["scores"]}
    if rec == "BUY":
        opposing = {a: v for a, v in scores.items() if v < 40}
    elif rec == "SELL":
        opposing = {a: v for a, v in scores.items() if v > 60}
    else:
        opposing = {a: v for a, v in scores.items() if v < 30 or v > 70}
    consensus = ctx["fundamental"]["analyst"].get("recommendation_key")
    sig, p = ctx["technical"]["signals"], ctx.get("predictive")
    facts = {
        "recommendation": rec,
        "radar_scores": scores,
        "opposing_axes": dict(sorted(opposing.items(), key=lambda kv: abs(kv[1] - 50), reverse=True)),
        "analyst_consensus": consensus,
        "analysts_disagree": (rec == "BUY" and consensus in _BEARISH) or (rec == "SELL" and consensus in _BULLISH),
        "levels": {
            "sma50": sig["trend"]["sma50"]["value"], "sma200": sig["trend"]["sma200"]["value"],
            "week52_high": ctx["fundamental"]["headline"]["week52_high"], "week52_low": ctx["fundamental"]["headline"]["week52_low"],
            "next_earnings": ctx["fundamental"]["earnings"]["next_date"],
            **(_month_range(ctx["technical"]["quote"]["price"], p["range"]["sigma_pct"]) if p else {}),
        },
    }
    # Only strong opposition is screened, and not for HOLD, where both directions argue against it.
    checks = [
        _check("counter-case", f"{axis} addressed", False, f"{axis} scores {score:.0f}/100, against the call, and isn't discussed.")
        for axis, score in opposing.items()
        if rec != "HOLD" and (score < 30 if rec == "BUY" else score > 70) and not re.search(_AXIS_WORDS[axis], text)
    ]
    return facts, checks


def _month_range(price: float, sigma_pct: float) -> dict:
    """Approximate 95% range over 20 trading days from the GARCH daily volatility (square-root-of-time)."""
    move = 1.96 * sigma_pct / 100 * math.sqrt(20)
    return {"range_20d_95_low": price * math.exp(-move), "range_20d_95_high": price * math.exp(move)}


def _valuation_sanity(ctx: dict, ai: dict, text: str, _: dict) -> tuple[dict, list] | None:
    target = ai["price_target"]
    if target is None and ai["recommendation"] != "BUY":
        return None
    f, price = ctx["fundamental"], ctx["technical"]["quote"]["price"]
    h, a = f["headline"], f["analyst"]
    pe_row = next((r for r in (f.get("history") or {}).get("rows", []) if r["key"] == "pe"), None)
    implied_pe = h["pe"] * target / price if target and h["pe"] and price else None
    valuation_score = next((x["score"] for x in ctx["scores"] if x["axis"] == "Valuation"), None)
    facts = {
        "price": price,
        "target": target,
        "target_upside_pct": _pct(target, price),
        "analyst_targets": {"mean": a.get("target_mean"), "low": a.get("target_low"), "high": a.get("target_high"), "count": a.get("analyst_count")},
        "pe_now": h["pe"], "forward_pe_now": h["forward_pe"], "loss_making": h["loss_making"],
        "pe_implied_by_target": implied_pe,
        "forward_pe_implied_by_target": h["forward_pe"] * target / price if target and h["forward_pe"] and price else None,
        "pe_history": pe_row and {"years": (f.get("history") or {}).get("years"), "median": pe_row["median"], "low": pe_row["low"], "high": pe_row["high"]},
        "history_verdicts": {r["label"]: r["verdict"] for r in (f.get("history") or {}).get("rows", []) if r["valuation"] and r.get("verdict")},
        "valuation_radar_score": valuation_score,
    }
    checks = []
    if target and a.get("target_high"):
        above = target > a["target_high"]
        checks.append(_check("valuation-sanity", "Target vs analysts", not above,
                             f"Target {target:.2f} is {'above' if above else 'within'} the analysts' range "
                             f"({_fmt(a.get('target_low'))}–{a['target_high']:.2f})."))
    if implied_pe and pe_row and pe_row["high"]:
        above = implied_pe > pe_row["high"]
        checks.append(_check("valuation-sanity", "Implied P/E", not above,
                             f"The target implies a P/E of {implied_pe:.1f} at today's earnings, against a fiscal-year range of "
                             f"{pe_row['low']:.1f}–{pe_row['high']:.1f}."))
    if valuation_score is not None:
        if valuation_score < 40 and _asserts(text, r"undervalued|cheap|attractive(ly)? valu|bargain|discount to"):
            checks.append(_check("valuation-sanity", "Valuation claim", False, f"Calls the stock cheap, but valuation scores {valuation_score:.0f}/100."))
        if valuation_score > 60 and _asserts(text, r"overvalued|expensive|stretched valu|rich valu"):
            checks.append(_check("valuation-sanity", "Valuation claim", False, f"Calls the stock expensive, but valuation scores {valuation_score:.0f}/100."))
    return facts, checks


def _fmt(x: float | None) -> str:
    return "n/a" if x is None else f"{x:.2f}"


def _earnings_window(ctx: dict, ai: dict, text: str, _: dict) -> tuple[dict, list] | None:
    e = ctx["fundamental"]["earnings"]
    days = _days_to(e["next_date"], date.fromisoformat(ctx["generated_at"][:10]))
    horizon = HORIZON_DAYS.get(ai["time_horizon"], 365)
    if days is None or not 0 <= days <= horizon:
        return None
    graded = [x for x in e["surprises"] if x["surprise_pct"] is not None]
    year = next((x for x in e["estimates"] if x["period"] == "0y"), None)
    facts = {
        "next_report": e["next_date"], "days_to_report": days, "horizon_days": horizon,
        "beats": e["beats"], "quarters_graded": len(graded),
        "latest_surprise_pct": graded[-1]["surprise_pct"] if graded else None,
        "current_year_eps_estimate_change_90d_pct": year and year["change_90d"],
        "revisions_30d": year and {"up": year["up_30d"], "down": year["down_30d"]},
    }
    checks = []
    if days <= 30:
        mentioned = bool(re.search(r"earnings|report|results|\beps\b|quarter", text))
        checks.append(_check("earnings-window", "Report acknowledged", mentioned,
                             f"The next report is in {days} days ({e['next_date']}); "
                             + ("the recommendation mentions it." if mentioned else "the recommendation doesn't mention earnings.")))
    change = year and year["change_90d"]
    if change is not None and ((ai["recommendation"] == "BUY" and change < -2) or (ai["recommendation"] == "SELL" and change > 2)):
        checks.append(_check("earnings-window", "Revisions vs call", False,
                             f"Current-year EPS estimates have moved {change:+.1f}% in 90 days, against a {ai['recommendation']}."))
    return facts, checks


# Which back-test indicators a mention in the recommendation refers to.
_INDICATORS = {
    "rsi": r"\brsi\b|overbought|oversold",
    "macd": r"\bmacd\b",
    "bollinger": r"bollinger|%b\b",
    "sma200": r"200[- ]day|golden cross|death cross|moving average|\bsma\b",
    "high52w": r"52[- ]week high",
    "adx": r"\badx\b|directional",
}


_INDICATOR_LABEL = {"rsi": "RSI", "macd": "MACD", "bollinger": "Bollinger Bands", "sma200": "Moving averages",
                    "high52w": "52-week high", "adx": "ADX"}


# Whether each back-test signal's condition still holds, from the current readings.
_HOLDS: dict[str, Callable[[dict], bool]] = {
    "rsi_oversold": lambda g: (g["rsi"]["value"] or 50) < 30,
    "rsi_overbought": lambda g: (g["rsi"]["value"] or 50) > 70,
    "macd_bull": lambda g: g["macd"]["state"] == "bullish",
    "macd_bear": lambda g: g["macd"]["state"] == "bearish",
    "bb_below": lambda g: g["bollinger"]["percent_b"] is not None and g["bollinger"]["percent_b"] < 0,
    "bb_above": lambda g: g["bollinger"]["percent_b"] is not None and g["bollinger"]["percent_b"] > 1,
    "above_200": lambda g: g["trend"]["sma200"]["value"] is not None and g["trend"]["sma200"]["price_above"],
    "below_200": lambda g: g["trend"]["sma200"]["value"] is not None and not g["trend"]["sma200"]["price_above"],
    "golden_cross": lambda g: g["trend"]["golden_cross"] is True,
    "death_cross": lambda g: g["trend"]["golden_cross"] is False,
    "high_52w": lambda g: g["high_52w"]["distance"] is not None and g["high_52w"]["distance"] > -0.01,
    "adx_up": lambda g: (g["adx"]["value"] or 0) > 25 and g["adx"]["direction"] == "up",
    "adx_down": lambda g: (g["adx"]["value"] or 0) > 25 and g["adx"]["direction"] == "down",
}


def _technical_evidence(ctx: dict, ai: dict, text: str, extra: dict) -> tuple[dict, list] | None:
    cited = [k for k, pattern in _INDICATORS.items() if re.search(pattern, text)]
    if not cited:
        return None
    bt = technical.backtest(ctx["symbol"], 14, 12, 26, 20, 2.0)
    if not bt:
        return None
    end, sig = date.fromisoformat(bt["end"]), ctx["technical"]["signals"]
    by_indicator, checks = {}, []
    for sgl in bt["signals"]:
        if sgl["indicator"] not in cited:
            continue
        h20 = next(h for h in sgl["horizons"] if h["days"] == 20)
        # A signal that fired recently and still holds is one the recommendation may be reading as a prediction.
        holds = _HOLDS.get(sgl["id"], lambda _: False)(sig)
        recent = holds and sgl["last"] is not None and (end - date.fromisoformat(sgl["last"])).days <= RECENT_SIGNAL_DAYS
        by_indicator.setdefault(sgl["indicator"], []).append({
            "signal": sgl["label"], "expects": sgl["expect"], "times_fired": sgl["count"], "last_fired": sgl["last"],
            "holds_now": holds, "fired_recently": recent, "hit_rate_20d": h20["hit_rate"], "base_rate_20d": h20["baseline_hit"], "verdict_20d": h20["verdict"],
        })
        if recent and h20["verdict"] in ("no_edge", "failed"):
            checks.append(_check("technical-evidence", sgl["label"], False,
                                 f"Fired on {sgl['last']}. On this stock, the price moved as expected 20 days later "
                                 f"{h20['hit_rate'] * 100:.0f}% of the time against {h20['baseline_hit'] * 100:.0f}% on all days "
                                 f"({'worse than chance' if h20['verdict'] == 'failed' else 'no edge'}, {sgl['count']} times in five years)."))
    facts = {"period": f"{bt['start']} to {bt['end']}", "cited_indicators": by_indicator}
    return facts, checks


def _entry_plan(ctx: dict, ai: dict, text: str, extra: dict) -> tuple[dict, list] | None:
    if ai["recommendation"] != "BUY" and not (ai["recommendation"] == "HOLD" and _adds(ai)):
        return None
    t, f, p = ctx["technical"], ctx["fundamental"], ctx.get("predictive")
    price, sig = t["quote"]["price"], t["signals"]
    r = p["range"] if p else None
    facts = {
        "price": price,
        "daily_volatility_pct": r and r["sigma_pct"],
        "long_run_daily_volatility_pct": r and r["long_run_sigma_pct"],
        "volatility_ratio": r and r["long_run_sigma_pct"] and r["sigma_pct"] / r["long_run_sigma_pct"],
        **({"range_20d_95_low_pct": _pct(_month_range(price, r["sigma_pct"])["range_20d_95_low"], price), **_month_range(price, r["sigma_pct"])} if r else {}),
        "atr_pct_of_price": sig["atr"]["pct"],
        "from_52w_high_pct": None if sig["high_52w"]["distance"] is None else sig["high_52w"]["distance"] * 100,
        "sma50": sig["trend"]["sma50"]["value"], "sma200": sig["trend"]["sma200"]["value"],
        "next_earnings": f["earnings"]["next_date"],
        "days_to_report": _days_to(f["earnings"]["next_date"], date.fromisoformat(ctx["generated_at"][:10])),
        "portfolio_weight_pct": extra.get("weight_pct"),
    }
    return facts, []


def _position_review(ctx: dict, ai: dict, text: str, extra: dict) -> tuple[dict, list] | None:
    pos = ctx.get("position")
    if not pos:
        return None
    weight = extra.get("weight_pct")
    facts = {
        "shares": pos["quantity"], "lots": pos["lots"], "avg_cost": pos["avg_cost"], "currency": pos["currency"],
        "unrealized_pct": pos["unrealized_pct"],
        "portfolio_weight_pct": weight, "holdings_in_portfolio": extra.get("holdings"),
        "largest_other_weight_pct": extra.get("largest_other_pct"),
        "position_advice": ai["position_advice"],
    }
    advice = ai["position_advice"].lower()
    checks = []
    if re.search(r"average cost|avg\.? cost|cost basis|break[- ]?even|purchase price|what you paid|get back to|recoup|recover (your|the) (loss|cost)", advice):
        checks.append(_check("position-review", "Anchoring", False, "The advice refers to your purchase price; check that it isn't the reason for the call."))
    if weight is not None and weight > CONCENTRATED_PCT and _adds(ai):
        checks.append(_check("position-review", "Concentration", "concentrat" in advice,
                             f"Advises adding to a position that is already {weight:.0f}% of the portfolio."))
    sells = re.search(r"\b(sell|trim|reduce|exit|take profits?)\b", advice)
    if (_adds(ai) and ai["recommendation"] == "SELL") or (sells and not _adds(ai) and ai["recommendation"] == "BUY"):
        checks.append(_check("position-review", "Advice vs call", False, f"The position advice doesn't match the {ai['recommendation']} call."))
    return facts, checks


FACTS: dict[str, Callable] = {
    "claim-check": _claim_check,
    "counter-case": _counter_case,
    "valuation-sanity": _valuation_sanity,
    "earnings-window": _earnings_window,
    "technical-evidence": _technical_evidence,
    "entry-plan": _entry_plan,
    "position-review": _position_review,
}


def _portfolio_extra(username: str, ctx: dict) -> dict:
    """The stock's share of the portfolio, for the sizing and position skills."""
    pos = ctx.get("position")
    if not pos:
        return {}
    try:
        m = portfolio.metrics(username, pos["currency"])
    except Exception:
        return {}
    weights: dict[str, float] = {}
    for row in m["rows"]:
        weights[row["symbol"]] = weights.get(row["symbol"], 0.0) + row["weight"]
    if ctx["symbol"] not in weights:
        return {}
    others = [w for s, w in weights.items() if s != ctx["symbol"]]
    return {"weight_pct": weights[ctx["symbol"]], "holdings": len(weights), "largest_other_pct": max(others) if others else None}


def select(username: str, ctx: dict, ai: dict) -> list[dict]:
    """Run each skill's facts function; the ones that return facts apply."""
    text, extra = _text(ai), _portfolio_extra(username, ctx)
    chosen = []
    for name, fn in FACTS.items():
        result = fn(ctx, ai, text, extra)
        if result is not None:
            facts, checks = result
            chosen.append({"name": name, "facts": _round(facts), "checks": checks})
    return chosen


# ── Gemini ───────────────────────────────────────────────────────────────────

class Finding(BaseModel):
    skill: str = Field(description="Name of the skill this finding comes from")
    stance: Literal["supports", "challenges", "neutral"]
    severity: Literal["info", "minor", "major"]
    finding: str = Field(description="One or two sentences, citing the numbers involved")


class EntryPlan(BaseModel):
    approach: Literal["all_at_once", "staged", "wait"]
    detail: str = Field(description="How to carry it out, e.g. number of purchases and spacing")
    size: str = Field(description="Sizing guidance from the volatility figures")
    review_when: str = Field(description="A date or event to re-check the call")


class Evaluation(BaseModel):
    verdict: Literal["stands", "weakened", "contradicted"]
    confidence_adjusted: int = Field(ge=1, le=10)
    summary: str = Field(description="Two or three sentences: the most important things the review found")
    findings: list[Finding]
    counter_case: str = Field(description="The strongest specific case against the recommendation")
    invalidation: list[str] = Field(description="2-4 observable conditions that would show the call is wrong")
    entry_plan: EntryPlan | None = Field(description="Only when the entry-plan skill is included; otherwise null")


def _prompt(ctx: dict, ai: dict, chosen: list[dict]) -> str:
    library = skills()
    review = {k: ai[k] for k in ("recommendation", "confidence", "time_horizon", "price_target", "summary",
                                 "strengths", "risks", "position_advice", "steps")}
    lines = [
        f"You are reviewing another analyst's recommendation on {ctx['symbol']} ({ctx['fundamental']['profile']['name']}), "
        f"made on {ctx['generated_at'][:10]}. Check it using the skills below; do not redo the analysis.",
        "",
        "Rules:",
        "- Use only the facts given here. If a skill needs something the facts don't cover, say so rather than guess.",
        "- You can't change the recommendation. You can lower confidence_adjusted when you find problems; never raise it "
        f"above the original {ai['confidence']}.",
        "- verdict: 'stands' if you find no major challenges; 'weakened' if there are minor challenges or one major one "
        "that doesn't carry the argument; 'contradicted' if the main argument rests on claims that are wrong or unreliable.",
        "- Automatic screens come from simple text rules and can misread phrasing. For each failed screen, read the wording "
        "it quotes or describes: confirm it as a challenge only if the recommendation really makes that claim; otherwise "
        "dismiss it in a 'neutral' info finding.",
        "- Every finding names the skill it comes from. Be concise and specific.",
        "",
        "RECOMMENDATION UNDER REVIEW",
        json.dumps(review, ensure_ascii=False),
    ]
    for i, item in enumerate(chosen, 1):
        skill = library[item["name"]]
        lines += ["", f"=== SKILL {i}: {item['name']} ===", skill["body"], "", "Facts:", json.dumps(item["facts"], ensure_ascii=False)]
        failed = [c for c in item["checks"] if not c["passed"]]
        if failed:
            lines += ["Automatic screens that failed:", *(f"- {c['check']}: {c['detail']}" for c in failed)]
    if not any(c["name"] == "entry-plan" for c in chosen):
        lines += ["", "The entry-plan skill doesn't apply: set entry_plan to null."]
    return "\n".join(lines)


def enforce(out: dict, ai: dict, names: list[str]) -> dict:
    """Hold the model to the rules it was given: it may only lower confidence, findings must come
    from a selected skill, "stands" means no major challenge, and only entry-plan gives a plan."""
    out = {**out, "confidence_adjusted": min(out["confidence_adjusted"], ai["confidence"])}
    out["findings"] = [x for x in out["findings"] if x["skill"] in names]
    if out["verdict"] == "stands" and any(x["stance"] == "challenges" and x["severity"] == "major" for x in out["findings"]):
        out["verdict"] = "weakened"
    if "entry-plan" not in names:
        out["entry_plan"] = None
    return out


def evaluate(username: str, ctx: dict, ai: dict) -> dict:
    if not GEMINI_AVAILABLE:
        raise RuntimeError("The google-genai package is not installed.")
    if not is_gemini_api_configured():
        raise RuntimeError("GEMINI_API_KEY is not configured in .env.")
    Assessment.model_validate({k: ai[k] for k in Assessment.model_fields})  # ValueError on a malformed result

    from google import genai

    chosen = select(username, ctx, ai)
    prompt = _prompt(ctx, ai, chosen)
    try:
        client = genai.Client(api_key=get_gemini_api_key())
        response = client.models.generate_content(
            model=MODEL,
            contents=prompt,
            config={
                "response_mime_type": "application/json",
                "response_schema": Evaluation,
                "thinking_config": {"thinking_level": THINKING_LEVEL},
                "automatic_function_calling": {"disable": True},
            },
        )
        if response.parsed is None and not response.text:
            reason = response.candidates[0].finish_reason if response.candidates else "no candidates"
            raise RuntimeError(f"empty response ({reason})")
        result: Evaluation = response.parsed or Evaluation.model_validate_json(response.text)
    except Exception as e:
        usage.log_call(MODEL, prompt, "", "assessment_evaluation", ctx["symbol"], success=False, error_message=str(e))
        raise RuntimeError(f"Gemini request failed: {e}") from e

    meta = getattr(response, "usage_metadata", None)
    usage.log_call(
        MODEL, prompt, response.text or "", "assessment_evaluation", ctx["symbol"],
        input_tokens=getattr(meta, "prompt_token_count", None),
        output_tokens=None if meta is None or meta.candidates_token_count is None
        else meta.candidates_token_count + (meta.thoughts_token_count or 0),
    )

    names = [c["name"] for c in chosen]
    out = enforce(result.model_dump(), ai, names)

    library = skills()
    out.update({
        "recommendation": ai["recommendation"],
        "original_confidence": ai["confidence"],
        "skills": [{k: library[n][k] for k in ("name", "title", "description", "applies_when", "evidence", "rationale", "sources")} for n in names],
        "checks": [c for item in chosen for c in item["checks"]],
        "model": MODEL,
        "generated_at": datetime.now().isoformat(),
    })
    out["saved"] = update_history(username, ctx["symbol"], ai["generated_at"], {"evaluation": {
        k: out[k] for k in ("verdict", "confidence_adjusted", "summary", "findings", "counter_case", "invalidation",
                            "entry_plan", "generated_at")
    } | {"skills": names}})
    return out
