"""Investment assessment: combine technical, fundamental, sentiment and ML signals,
then ask Gemini for a structured recommendation."""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from config import GEMINI_AVAILABLE, get_gemini_api_key, is_gemini_api_configured, normalize_symbol

from . import fundamentals, market, predictive, sentiment, technical, usage
from .storage import append_history, load_holdings

MODEL = "gemini-2.5-flash"


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


def _scores(tech: dict, fund: dict, pred: dict | None, sent: dict | None) -> list[dict]:
    """0-100 scores for the radar chart. 50 means neutral / unknown."""
    ratios = {r["label"]: r["value"] for group in fund["ratios"].values() for r in group}
    pe = ratios.get("P/E")
    growth = ratios.get("Revenue Growth")
    roe = ratios.get("Return on Equity")
    de = ratios.get("Debt / Equity")  # yfinance reports as percent, e.g. 150 == 1.5x
    momentum = _momentum(tech["signals"])
    return [
        {"axis": "Valuation", "score": _clamp(100 - (pe - 15) * 2) if pe else 50},
        {"axis": "Growth", "score": _clamp((growth * 100 + 20) * 2.5) if growth is not None else 50},
        {"axis": "Profitability", "score": _clamp(roe * 100 * 4) if roe is not None else 50},
        {"axis": "Momentum", "score": momentum if momentum is not None else 50},
        {"axis": "Balance sheet", "score": _clamp(100 - de / 100 * 40) if de is not None else 50},
        {"axis": "Sentiment", "score": _clamp((sent["avg_vader"] + 1) * 50) if sent and sent["total"] else 50},
        {"axis": "Model accuracy", "score": _clamp(pred["directional_accuracy"] * 100)
            if pred and pred.get("directional_accuracy") is not None else 50},
    ]


def build_context(username: str, symbol: str, period: str, include_sentiment: bool) -> dict:
    """Run every analysis the AI needs. Returns a JSON-safe context dict."""
    symbol = normalize_symbol(symbol)
    sentiment_on = include_sentiment and sentiment.status()["enabled"]

    with ThreadPoolExecutor(max_workers=4) as pool:
        tech_f = pool.submit(technical.analyze, symbol, period, 14, 12, 26, 20, 2.0)
        fund_f = pool.submit(fundamentals.analyze, symbol)
        pred_f = pool.submit(predictive.quick, symbol, period)
        sent_f = pool.submit(sentiment.analyze, symbol, 15, "both") if sentiment_on else None
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
            for a in sent["articles"][:6]
        ]
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
    steps: list[ReasoningStep] = Field(description="Step-by-step reasoning: technical, fundamental, sentiment, predictive, position, synthesis")
    recommendation: Literal["BUY", "HOLD", "SELL"]
    confidence: int = Field(ge=1, le=10)
    time_horizon: Literal["Short-term", "Medium-term", "Long-term"]
    price_target: float | None = Field(description="12-month price target in the stock's currency, or null")
    strengths: list[str]
    risks: list[str]
    position_advice: str = Field(description="Whether to add to, reduce, or hold the current position, and why")
    summary: str = Field(description="One-paragraph final reasoning")


def _fmt(value, spec: str = ".2f", suffix: str = "") -> str:
    return "n/a" if value is None else f"{value:{spec}}{suffix}"


def _pct(fraction: float | None) -> float | None:
    return None if fraction is None else fraction * 100


def _prompt(ctx: dict) -> str:
    t, f = ctx["technical"], ctx["fundamental"]
    sig = t["signals"]
    ratios = {r["label"]: r for group in f["ratios"].values() for r in group}

    def ratio(label: str) -> str:
        r = ratios.get(label)
        if not r or r["value"] is None:
            return "n/a"
        return f"{r['value'] * 100:.1f}%" if r["unit"] == "fraction" else f"{r['value']:.2f}"

    lines = [
        f"You are a professional equity analyst. Assess {ctx['symbol']} ({f['profile']['name']}, "
        f"{f['profile'].get('sector') or 'sector n/a'}) and give a BUY, HOLD or SELL recommendation.",
        "",
        "TECHNICAL",
        f"- Price {_fmt(t['quote']['price'])} ({_fmt(t['quote']['change_pct'], '+.2f', '%')} on the day)",
        f"- RSI(14) {_fmt(sig['rsi']['value'])} ({sig['rsi']['state']}; extremes mean stretched, not a reversal "
        f"signal on their own, and RSI can stay above 70 through strong uptrends)",
        f"- MACD {sig['macd']['state']} (MACD {_fmt(sig['macd']['macd'], '.3f')} vs signal {_fmt(sig['macd']['signal'], '.3f')})",
        f"- Bollinger %B {_fmt(sig['bollinger']['percent_b'])} ({sig['bollinger']['state']} bands)",
        f"- Price {'above' if sig['trend']['sma50']['price_above'] else 'below'} 50-day SMA ({_fmt(sig['trend']['sma50']['value'])}); OBV {sig['obv']['state']}",
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
        f"- P/E {ratio('P/E')}, forward P/E {ratio('Forward P/E')}, PEG {ratio('PEG')}, P/B {ratio('Price / Book')}",
        f"- ROE {ratio('Return on Equity')}, profit margin {ratio('Profit Margin')}, revenue growth {ratio('Revenue Growth')}",
        f"- Debt/Equity {ratio('Debt / Equity')} (percent), current ratio {ratio('Current Ratio')}",
        f"- Analyst consensus {f['analyst'].get('recommendation_key') or 'n/a'}, mean target {_fmt(f['analyst'].get('target_mean'))} "
        f"({_fmt(f['analyst'].get('upside_pct'), '+.1f', '%')} upside)",
    ]
    p = ctx.get("predictive")
    if p:
        lines += ["", "MACHINE LEARNING (Random Forest, next-session close)",
                  f"- Forecast {_fmt(p['next_close'])} vs last close {_fmt(p['last_close'])}",
                  f"- Backtest RMSE {_fmt(p['rmse'], '.3f')}, directional accuracy {_fmt((p['directional_accuracy'] or 0) * 100, '.1f', '%')}",
                  f"- Top features: {', '.join(x['feature'] for x in p['top_features'][:3])}"]
    s = ctx.get("sentiment")
    if s and s["total"]:
        lines += ["", "NEWS SENTIMENT",
                  f"- {s['overall']} overall; VADER {s['avg_vader']:+.3f} across {s['total']} articles "
                  f"({s['pct']['Positive']:.0f}% positive / {s['pct']['Negative']:.0f}% negative)",
                  *[f"- \"{h['title']}\" ({h['source']})" for h in s.get("headlines", [])[:5]]]
    pos = ctx.get("position")
    if pos:
        lines += ["", "CURRENT POSITION",
                  f"- {pos['quantity']:.2f} shares at average cost {_fmt(pos['avg_cost'])} {pos['currency']}",
                  f"- Unrealized {_fmt(pos['unrealized_pct'], '+.2f', '%')}"]
    lines += ["", "Weigh where the signals agree or diverge. Be specific and concise; do not invent data that is not given."]
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
            config={"response_mime_type": "application/json", "response_schema": Assessment},
        )
        result: Assessment = response.parsed or Assessment.model_validate_json(response.text)
    except Exception as e:
        usage.log_call(MODEL, prompt, "", "investment_assessment", ctx["symbol"], success=False, error_message=str(e))
        raise RuntimeError(f"Gemini request failed: {e}") from e

    meta = getattr(response, "usage_metadata", None)
    usage.log_call(
        MODEL, prompt, response.text or "", "investment_assessment", ctx["symbol"],
        input_tokens=getattr(meta, "prompt_token_count", None),
        output_tokens=getattr(meta, "candidates_token_count", None),
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
