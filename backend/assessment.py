"""Investment assessment: combine technical, fundamental, sentiment and ML signals,
then ask Gemini for a structured recommendation."""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from config import GEMINI_AVAILABLE, get_gemini_api_key, is_gemini_api_configured, normalize_symbol

from . import fundamentals, market, predictive, sentiment, technical, usage
from .storage import append_history, load_holdings

MODEL = "gemini-3.5-flash-lite"
# Gemini 3 models think before answering; "minimal" is this model's default. "low" leaves room
# to weigh conflicting signals without much extra cost (thinking tokens bill as output).
THINKING_LEVEL = "low"


def _portfolio_position(username: str, symbol: str) -> dict | None:
    lots = [h for h in load_holdings(username) if h["Symbol"] == symbol]
    if not lots:
        return None
    qty = sum(float(h["Quantity"]) for h in lots)
    invested = sum(float(h["Quantity"]) * float(h["Purchase_Price"]) for h in lots)
    price = market.price(symbol)
    value = qty * price if price else None
    return {
        "lots": len(lots),
        "quantity": qty,
        "avg_cost": invested / qty if qty else None,
        "invested": invested,
        "value": value,
        "unrealized": value - invested if value is not None else None,
        "unrealized_pct": (value - invested) / invested * 100 if value is not None and invested else None,
        "currency": lots[0]["Currency"],
    }


def _clamp(x: float) -> float:
    return max(0.0, min(100.0, x))


def _momentum(signals: dict) -> float | None:
    """Directional momentum, 50 = neutral. Equal-weight blend of whichever are available:
    RSI (higher = stronger), 12-1 month return (0% -> 50, +50% -> 100), and the share of
    trend confirmations (price above SMA 20 / 50 / 200, MACD above signal)."""
    trend = signals["trend"]
    confirms = [trend[k]["price_above"] for k in ("sma20", "sma50", "sma200") if trend[k]["value"] is not None]
    if signals["macd"]["state"] is not None:
        confirms.append(signals["macd"]["state"] == "bullish")
    rsi, ret = signals["rsi"]["value"], signals["momentum"]["return_12_1"]
    parts = [p for p in (
        rsi,
        _clamp(50 + ret * 100) if ret is not None else None,
        100 * sum(confirms) / len(confirms) if confirms else None,
    ) if p is not None]
    return _clamp(sum(parts) / len(parts)) if parts else None


def _mean(parts: list[float | None]) -> float | None:
    parts = [x for x in parts if x is not None]
    return sum(parts) / len(parts) if parts else None


def _fundamental_scores(fund: dict) -> dict[str, float | None]:
    """Absolute rules of thumb; without sector data a score can't say "cheap for its industry"."""
    r = {x["key"]: x["value"] for group in fund["ratios"].values() for x in group}
    m = {x["key"]: x["value"] for x in fund["quality"]["metrics"] + fund["risk"]["metrics"]}
    h, financial = fund["headline"], fund["profile"].get("kind") == "financial"

    # Valuation on yields rather than P/E, so loss-makers score low instead of neutral.
    # A 10% earnings yield (P/E 10) scores 100; 5% (P/E 20) scores 50.
    earnings_yield = -0.05 if h.get("loss_making") else 1 / r["trailingPE"] if r.get("trailingPE") else None
    ev_ebitda = r.get("enterpriseToEbitda")
    absolute = _mean([
        None if earnings_yield is None else _clamp(earnings_yield * 1000),
        None if ev_ebitda is None else _clamp(100 - (ev_ebitda - 6) * 4),  # 6x → 100, 31x → 0
    ])
    # Against the company's own fiscal-year history: 20% cheaper than its median scores 70.
    relative = _mean([
        _clamp(50 + (row["vs_median"] if row["better"] == "higher" else -row["vs_median"]) * 100)
        for row in fund.get("history", {}).get("rows", []) if row["valuation"] and row["vs_median"] is not None
    ])
    valuation = _mean([absolute, relative])

    growth = r.get("annualRevenueGrowth")
    if growth is None:
        growth = r.get("revenueGrowth")

    # ROE suits banks; for other companies ROA and operating margin aren't distorted by buybacks.
    if financial:
        profitability = None if r.get("returnOnEquity") is None else _clamp(r["returnOnEquity"] * 500)
    else:
        profitability = _mean([
            None if r.get("returnOnAssets") is None else _clamp(r["returnOnAssets"] * 500),     # 20% → 100
            None if r.get("operatingMargins") is None else _clamp(r["operatingMargins"] * 250),  # 40% → 100
            None if m.get("gross_profitability") is None else _clamp(m["gross_profitability"] * 250),  # 40% → 100
        ])

    de, current = r.get("debtToEquity"), r.get("currentRatio")  # D/E in percent: 150 == 1.5x
    z, cover, net_debt = m.get("altman_z"), m.get("interest_coverage"), m.get("net_debt_ebitda")
    balance = _mean([
        None if de is None else _clamp(100 - de / 100 * 40),
        None if current is None else _clamp((current - 0.5) * 100),  # 1.0 → 50, 1.5 → 100
        None if z is None else _clamp(25 + (z - 1.1) / 1.5 * 50),     # distress line 25, safe line 75
        None if cover is None else _clamp(cover * 10),                # 10x → 100
        None if net_debt is None else _clamp(100 - net_debt * 25),    # net cash → 100, 4x → 0
    ])

    f_score = fund["quality"]["piotroski"]
    earn = fund["earnings"]
    graded = [x for x in earn["surprises"] if x["surprise_pct"] is not None]
    year = next((x for x in earn["estimates"] if x["period"] == "0y"), None)
    earnings = _mean([
        earn["beats"] / len(graded) * 100 if graded else None,
        None if not year or year["change_90d"] is None else _clamp(50 + year["change_90d"] * 5),  # +10% in 90 days → 100
    ])
    return {
        "Valuation": valuation,
        "Growth": None if growth is None else _clamp((growth * 100 + 20) * 2.5),
        "Profitability": profitability,
        "Balance sheet": balance,
        "Quality": f_score["score"] / f_score["tested"] * 100 if f_score else None,
        "Earnings": earnings,
    }


def _forecast_score(pred: dict | None) -> float | None:
    """Above 50 only when a model beat the no-change forecast out of sample and expects a
    rise; scaled by tomorrow's expected move relative to its typical daily move. A model
    without demonstrated skill scores a neutral 50, whatever it predicts."""
    if not pred or not pred["best"] or pred["best"]["verdict"] != "skill":
        return None
    sigma = pred["range"]["sigma_pct"] / 100
    return _clamp(50 + pred["best"]["next_return"] / sigma * 50) if sigma else None


def _sentiment_score(sent: dict | None) -> float | None:
    """News tone mapped to 0-100, but only when its 95% interval excludes zero; a tone that
    can't be told apart from neutral scores 50."""
    if not sent or sent["overall"] not in ("Positive", "Negative"):
        return None
    return _clamp(50 + sent["index"] * 50)


def _scores(tech: dict, fund: dict, pred: dict | None, sent: dict | None) -> list[dict]:
    """0-100 scores for the radar chart. 50 means neutral / unknown."""
    f = _fundamental_scores(fund)
    raw = {
        "Valuation": f["Valuation"],
        "Growth": f["Growth"],
        "Profitability": f["Profitability"],
        "Momentum": _momentum(tech["signals"]),
        "Balance sheet": f["Balance sheet"],
        "Quality": f["Quality"],
        "Earnings": f["Earnings"],
        "Sentiment": _sentiment_score(sent),
        "Forecast": _forecast_score(pred),
    }
    return [{"axis": axis, "score": 50 if score is None else score} for axis, score in raw.items()]


def build_context(username: str, symbol: str, period: str, include_sentiment: bool) -> dict:
    """Run every analysis the AI needs. Returns a JSON-safe context dict."""
    symbol = normalize_symbol(symbol)
    sentiment_on = include_sentiment and sentiment.status()["enabled"]

    with ThreadPoolExecutor(max_workers=4) as pool:
        tech_f = pool.submit(technical.analyze, symbol, period, 14, 12, 26, 20, 2.0)
        fund_f = pool.submit(fundamentals.analyze, symbol)
        pred_f = pool.submit(predictive.quick, symbol)
        sent_f = pool.submit(sentiment.analyze, symbol, 7, "both") if sentiment_on else None
        tech, fund, pred = tech_f.result(), fund_f.result(), pred_f.result()
        sent, sent_error = None, None
        if sent_f:
            try:
                sent = sent_f.result()
            except Exception as e:
                sent_error = str(e)

    if tech is None or fund is None:
        raise LookupError(f"Could not fetch market data for {symbol}. Yahoo Finance may be rate-limiting; try again shortly.")

    tech_light = {k: v for k, v in tech.items() if k != "series"}
    sent_light = None
    if sent:
        sent_light = {k: v for k, v in sent.items() if k != "articles"}
        sent_light["headlines"] = [
            {"title": a["title"], "source": a["source"], "date": a["date"], "sentiment": a["sentiment"], "link": a["link"]}
            # The strongest-toned headlines say most about what's driving the tone
            for a in sorted((a for a in sent["articles"] if a["status"] == "scored"), key=lambda a: -abs(a["score"]))
        ][:6]
    fund_light = {k: v for k, v in fund.items() if k != "statements"}

    return {
        "symbol": symbol,
        "period": period,
        "generated_at": datetime.now().isoformat(),
        "technical": tech_light,
        "fundamental": fund_light,
        "predictive": pred,
        "sentiment": sent_light,
        "sentiment_status": {"requested": include_sentiment, "enabled": sentiment.status()["enabled"], "error": sent_error},
        "position": _portfolio_position(username, symbol),
        "scores": _scores(tech, fund, pred, sent),
        "ai_available": GEMINI_AVAILABLE and is_gemini_api_configured(),
    }


# ── Gemini ───────────────────────────────────────────────────────────────────

class ReasoningStep(BaseModel):
    title: str = Field(description="Short title, e.g. 'Technical picture'")
    content: str = Field(description="2-5 sentences of reasoning for this step, in plain prose")


class Assessment(BaseModel):
    steps: list[ReasoningStep] = Field(description="Step-by-step reasoning, one step per section given in the prompt "
                                       "(technical, fundamental, then forecast, sentiment and position if present), then a synthesis")
    recommendation: Literal["BUY", "HOLD", "SELL"]
    confidence: int = Field(ge=1, le=10)
    time_horizon: Literal["Short-term", "Medium-term", "Long-term"]
    price_target: float | None = Field(description="12-month price target in the currency the price is quoted in, or null")
    strengths: list[str]
    risks: list[str]
    position_advice: str = Field(description="Whether to add to, reduce, or hold the current position, and why")
    summary: str = Field(description="One-paragraph final reasoning")


def _fmt(value, spec: str = ".2f", suffix: str = "") -> str:
    return "n/a" if value is None else f"{value:{spec}}{suffix}"


def _pct(fraction: float | None) -> float | None:
    return None if fraction is None else fraction * 100


def _metric_text(x: dict) -> str:
    v = x["value"]
    text = x["note"] or "n/a" if v is None else f"{v * 100:.1f}%" if x["unit"] == "fraction" else f"{v:.2f}"
    return f"{text} ({x['note']})" if v is not None and x["note"] else text


def _history_line(f: dict) -> list[str]:
    h = f.get("history") or {}
    if not h.get("rows"):
        return []

    def show(row: dict, v: float) -> str:
        return f"{v * 100:.1f}%" if row["unit"] == "fraction" else f"{v:.1f}"

    parts = [
        f"{row['label']} {show(row, row['now'])} vs median {show(row, row['median'])} "
        f"(range {show(row, row['low'])}–{show(row, row['high'])})"
        for row in h["rows"] if row["now"] is not None
    ]
    return [f"- Against its own fiscal-year history {h['years'][0]}–{h['years'][-1]} (now is trailing 12 months): "
            + "; ".join(parts)] if parts else []


def _quality_lines(f: dict) -> list[str]:
    lines = _history_line(f)
    fs = f["quality"]["piotroski"]
    if fs:
        lines.append(f"- Piotroski F-score {fs['score']}/{fs['tested']} ({fs['state']})")
    metrics = f["quality"]["metrics"] + f["risk"]["metrics"]
    lines.append("- " + ", ".join(f"{x['label']} {_metric_text(x)}" for x in metrics))
    e = f["earnings"]
    graded = [x for x in e["surprises"] if x["surprise_pct"] is not None]
    if graded:
        lines.append(f"- Beat EPS estimates in {e['beats']} of the last {len(graded)} quarters "
                     f"(latest surprise {graded[-1]['surprise_pct']:+.1f}%)")
    year = next((x for x in e["estimates"] if x["period"] == "0y"), None)
    if year and year["change_90d"] is not None:
        lines.append(f"- Current-year EPS estimate {year['change_90d']:+.1f}% over 90 days "
                     f"({_fmt(year['up_30d'], '.0f')} up / {_fmt(year['down_30d'], '.0f')} down revisions in 30 days)")
    if e["next_date"]:
        lines.append(f"- Next earnings report {e['next_date']}")
    return lines


def _prompt(ctx: dict) -> str:
    t, f = ctx["technical"], ctx["fundamental"]
    sig = t["signals"]
    ratios = {r["key"]: r for group in f["ratios"].values() for r in group}

    def ratio(key: str) -> str:
        r = ratios.get(key)
        if not r or r["value"] is None:
            return r["note"] if r and r.get("note") else "n/a"
        text = f"{r['value'] * 100:.1f}%" if r["unit"] == "fraction" else f"{r['value']:.2f}"
        return f"{text} ({r['note']})" if r.get("note") else text

    lines = [
        f"You are a professional equity analyst. Assess {ctx['symbol']} ({f['profile']['name']}, "
        f"{f['profile'].get('sector') or 'sector n/a'}) and give a BUY, HOLD or SELL recommendation.",
        f"Data as of {ctx['generated_at'][:10]}. Prices are in {f['profile'].get('currency') or 'the trading currency'}.",
        "",
        "TECHNICAL",
        f"- Price {_fmt(t['quote']['price'])} ({_fmt(t['quote']['change_pct'], '+.2f', '%')} on the day)",
        f"- RSI(14) {_fmt(sig['rsi']['value'])} ({sig['rsi']['state']}; extremes mean stretched, not a reversal "
        f"signal on their own, and RSI can stay above 70 through strong uptrends)",
        f"- MACD {sig['macd']['state']} (MACD {_fmt(sig['macd']['macd'], '.3f')} vs signal {_fmt(sig['macd']['signal'], '.3f')})",
        f"- Bollinger %B {_fmt(sig['bollinger']['percent_b'])} ({sig['bollinger']['state']} bands)",
        (f"- Price {'above' if sig['trend']['sma50']['price_above'] else 'below'} 50-day SMA ({_fmt(sig['trend']['sma50']['value'])}); "
         if sig["trend"]["sma50"]["value"] is not None else "- 50-day SMA n/a; ") + f"OBV {sig['obv']['state']}",
        f"- 200-day SMA {_fmt(sig['trend']['sma200']['value'])}"
        + ("" if sig["trend"]["sma200"]["value"] is None else f" (price {'above' if sig['trend']['sma200']['price_above'] else 'below'}; "
           f"50-day {'above' if sig['trend']['golden_cross'] else 'below'} 200-day)"),
        f"- 12-1 month momentum {_fmt(_pct(sig['momentum']['return_12_1']), '+.1f', '%')}; "
        f"{_fmt(_pct(sig['high_52w']['distance']), '+.1f', '%')} from 52-week high ({_fmt(sig['high_52w']['value'])})",
        f"- ADX(14) {_fmt(sig['adx']['value'], '.1f')} ({sig['adx']['state']} trend, {sig['adx']['direction']}: "
        f"+DI {_fmt(sig['adx']['plus_di'], '.1f')} vs -DI {_fmt(sig['adx']['minus_di'], '.1f')}); "
        f"ATR(14) {_fmt(sig['atr']['value'])} ({_fmt(sig['atr']['pct'], '.1f', '%')} of price)",
        "",
        "FUNDAMENTAL",
        *([f"- Note: {f['profile']['kind_note']}"] if f["profile"].get("kind_note") else []),
        f"- P/E {ratio('trailingPE')}, forward P/E {ratio('forwardPE')}, PEG {ratio('pegRatio')}, "
        f"P/B {ratio('priceToBook')}, EV/EBITDA {ratio('enterpriseToEbitda')}",
        f"- ROE {ratio('returnOnEquity')}, ROA {ratio('returnOnAssets')}, operating margin {ratio('operatingMargins')}, "
        f"profit margin {ratio('profitMargins')}",
        f"- Revenue growth {ratio('annualRevenueGrowth')} last fiscal year, {ratio('revenueGrowth')} latest quarter year on year",
        f"- Debt/Equity {ratio('debtToEquity')} (percent), current ratio {ratio('currentRatio')}, FCF yield {ratio('fcfYield')}",
        *_quality_lines(f),
        f"- Analyst consensus {f['analyst'].get('recommendation_key') or 'n/a'}, mean target {_fmt(f['analyst'].get('target_mean'))} "
        f"({_fmt(f['analyst'].get('upside_pct'), '+.1f', '%')} upside)",
    ]
    p = ctx.get("predictive")
    if p:
        lines += ["", f"FORECAST MODELS (next-session return, walk-forward test on the last {p['test_days']} days of 2 years)"]
        for m in p["models"]:
            ci = m["direction_ci"]
            lines.append(f"- {m['name']}: skill vs no-change forecast {_fmt(_pct(m['skill']), '+.2f', '%')} "
                         f"(Diebold-Mariano p {_fmt(m['dm_p'], '.2f')}) -> {m['verdict']}; direction right "
                         f"{_fmt(_pct(m['directional_accuracy']), '.0f', '%')}"
                         + (f" (95% CI {ci[0] * 100:.0f}-{ci[1] * 100:.0f}%)" if ci else "")
                         + f"; predicts {_fmt(m['next_return'] * 100, '+.2f', '%')} next session")
        lines.append(f"- Up days in the test window: {p['up_share'] * 100:.0f}% (an always-up guess scores this on direction)")
        if not p["any_skill"]:
            lines.append("- No model beat the no-change forecast with significance: treat the model forecasts as no signal.")
        r = p["range"]
        lines.append(f"- GARCH(1,1) next-session range: 80% {_fmt(r['next']['80']['low'])}-{_fmt(r['next']['80']['high'])}, "
                     f"95% {_fmt(r['next']['95']['low'])}-{_fmt(r['next']['95']['high'])} (last close {_fmt(p['last_close'])}); "
                     f"daily volatility {r['sigma_pct']:.2f}% vs long-run {_fmt(r['long_run_sigma_pct'], '.2f', '%')}; "
                     f"past 80% ranges held {_fmt(_pct(r['coverage']['80']['hit_rate']), '.0f', '%')} of closes")
    s = ctx.get("sentiment")
    if s and s["n"]:
        ci = s["ci"]
        tilt = {"Positive": "positive (95% CI excludes zero)", "Negative": "negative (95% CI excludes zero)",
                "Neutral": "no clear tilt (95% CI includes zero)", None: f"too few articles to judge (under {s['min_articles']})"}
        lines += ["", f"NEWS SENTIMENT (last {s['days']} days, firm-specific headlines scored by {s['scorer']['name']})",
                  f"- Net tone {s['index']:+.2f} on a -1 to +1 scale"
                  + (f" (95% CI {ci[0]:+.2f} to {ci[1]:+.2f})" if ci else "")
                  + f" across {s['n']} headlines: {tilt[s['overall']]}; "
                  f"{s['pct']['Positive']:.0f}% positive / {s['pct']['Negative']:.0f}% negative",
                  *([f"- Price moved {s['price']['change_pct']:+.1f}% over the same window; "
                     f"{s['price_move_share'] * 100:.0f}% of headlines report a price move, so tone partly reflects moves already made"]
                    if s.get("price") and s.get("price_move_share") is not None else []),
                  "- Research finds news tone predicts returns only weakly and for a day or two; treat it as context, not a forecast.",
                  *[f"- \"{h['title']}\" ({h['source']}, {h['sentiment'].lower()})" for h in s.get("headlines", [])[:5]]]
    pos = ctx.get("position")
    if pos:
        lines += ["", "CURRENT POSITION",
                  f"- {pos['quantity']:.2f} shares at average cost {_fmt(pos['avg_cost'])} {pos['currency']}",
                  f"- Unrealized {_fmt(pos['unrealized_pct'], '+.2f', '%')}"]
    lines += ["", "Weigh where the signals agree or diverge. Be specific and concise; do not invent data that is not given, "
              "and skip any section above that is missing rather than guessing at it."]
    return "\n".join(lines)


def generate(username: str, ctx: dict) -> dict:
    if not GEMINI_AVAILABLE:
        raise RuntimeError("The google-genai package is not installed.")
    if not is_gemini_api_configured():
        raise RuntimeError("GEMINI_API_KEY is not configured in .env.")

    from google import genai

    prompt = _prompt(ctx)
    try:
        client = genai.Client(api_key=get_gemini_api_key())
        response = client.models.generate_content(
            model=MODEL,
            contents=prompt,
            config={
                "response_mime_type": "application/json",
                "response_schema": Assessment,
                "thinking_config": {"thinking_level": THINKING_LEVEL},
                "automatic_function_calling": {"disable": True},  # no tools here
            },
        )
        if response.parsed is None and not response.text:
            reason = response.candidates[0].finish_reason if response.candidates else "no candidates"
            raise RuntimeError(f"empty response ({reason})")
        result: Assessment = response.parsed or Assessment.model_validate_json(response.text)
    except Exception as e:
        usage.log_call(MODEL, prompt, "", "investment_assessment", ctx["symbol"], success=False, error_message=str(e))
        raise RuntimeError(f"Gemini request failed: {e}") from e

    meta = getattr(response, "usage_metadata", None)
    usage.log_call(
        MODEL, prompt, response.text or "", "investment_assessment", ctx["symbol"],
        input_tokens=getattr(meta, "prompt_token_count", None),
        # Thinking tokens are billed as output but reported separately.
        output_tokens=None if meta is None or meta.candidates_token_count is None
        else meta.candidates_token_count + (meta.thoughts_token_count or 0),
    )

    out = result.model_dump()
    pos = ctx.get("position")
    append_history(username, {
        "timestamp": datetime.now().isoformat(),
        "symbol": ctx["symbol"],
        "recommendation": out["recommendation"],
        "confidence": out["confidence"],
        "price_at_signal": ctx["technical"]["quote"]["price"],
        "price_target": out["price_target"],
        "time_horizon": out["time_horizon"],
        "strengths": out["strengths"],
        "risks": out["risks"],
        "reasoning": out["summary"],
        "steps": out["steps"],
        "position_advice": out["position_advice"],
        "portfolio_context": pos and {
            "avg_purchase_price": pos["avg_cost"],
            "total_quantity": pos["quantity"],
            "unrealized_pct": pos["unrealized_pct"],
        },
    })
    return {**out, "model": MODEL, "generated_at": datetime.now().isoformat()}
