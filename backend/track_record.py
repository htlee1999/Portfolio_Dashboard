"""Hindsight scoring of past AI recommendations."""

from concurrent.futures import ThreadPoolExecutor

from . import market
from .storage import load_history


def _outcome(rec: str, signal_price, current_price) -> tuple[float | None, str]:
    if not signal_price or current_price is None:
        return None, "Pending"
    change = (current_price - signal_price) / signal_price * 100
    if rec == "BUY":
        return change, "Correct" if change > 0 else "Wrong"
    if rec == "SELL":
        # A SELL is "correct" if the price fell; its return is the loss avoided.
        return -change, "Correct" if change < 0 else "Wrong"
    return change, "Neutral"


def build(username: str) -> dict:
    history = load_history(username)
    symbols = sorted({h["symbol"] for h in history})
    with ThreadPoolExecutor(max_workers=8) as pool:
        prices = dict(zip(symbols, pool.map(market.price, symbols)))

    signals = []
    for i, h in enumerate(history):
        current = prices.get(h["symbol"])
        ret, outcome = _outcome(h.get("recommendation", "HOLD"), h.get("price_at_signal"), current)
        signals.append({
            "id": i,
            "timestamp": h["timestamp"],
            "symbol": h["symbol"],
            "recommendation": h.get("recommendation", "HOLD"),
            "confidence": h.get("confidence"),
            "price_at_signal": h.get("price_at_signal"),
            "current_price": current,
            "price_target": h.get("price_target"),
            "time_horizon": h.get("time_horizon"),
            "return_pct": ret,
            "outcome": outcome,
            "strengths": h.get("strengths", []),
            "risks": h.get("risks", []),
            "reasoning": h.get("reasoning", ""),
            "steps": h.get("steps", []),
            "position_advice": h.get("position_advice"),
            "portfolio_context": h.get("portfolio_context"),
            "evaluation": h.get("evaluation"),
        })
    signals.sort(key=lambda s: s["timestamp"], reverse=True)
    return {"signals": signals, "symbols": symbols}
