"""Hindsight scoring of past AI recommendations.

Each call is scored at fixed checkpoints after it was made, against the S&P 500 over the same days,
so calls of different ages are judged over the same length of time and a rising market doesn't
count as skill. Prices are split-adjusted closes, so a later split doesn't turn a BUY into a loss.
"""

from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime

import pandas as pd

from . import market
from .storage import load_history

BENCHMARK = "^GSPC"

# Checkpoints in trading days after the signal.
CHECKPOINTS = {5: "1W", 21: "1M", 63: "3M", 126: "6M", 252: "1Y"}

# Trading days each stated horizon covers, matching the calendar spans in evaluation.HORIZON_DAYS.
STATED_DAYS = {"Short-term": 63, "Medium-term": 252, "Long-term": 756}

# A call within this many percentage points of the S&P 500 is a draw, not a win or a loss.
FLAT_BAND = 1.0

# Price targets are 12-month targets.
TARGET_DAYS = 252

# Simple rules the AI is compared with, on the same stocks and dates. App-score cut-offs are on its 0-100 scale.
RULES = {"always_buy": "Always BUY", "momentum": "12-1 month momentum", "analyst": "Analyst consensus",
         "app_score": "App scores"}
_ANALYST = {"strong_buy": "BUY", "buy": "BUY", "hold": "HOLD", "underperform": "SELL", "sell": "SELL", "strong_sell": "SELL"}
APP_SCORE_BUY, APP_SCORE_SELL = 55, 45

# History timestamps are naive datetime.now() values, in the server's local time.
LOCAL_TZ = datetime.now().astimezone().tzinfo

# Below this gap between the entry close and the quoted price, the quote is stale or intraday, not split.
SPLIT_GAP = 1.4


def _outcome(rec: str, excess: float | None) -> tuple[float | None, str]:
    """Directional return vs the benchmark, and the outcome. A SELL's return is the underperformance avoided."""
    if excess is None:
        return None, "Pending"
    if rec == "HOLD":
        return excess, "Neutral"
    ret = excess if rec == "BUY" else -excess
    if abs(ret) <= FLAT_BAND:
        return ret, "Flat"
    return ret, "Correct" if ret > 0 else "Wrong"


def _pct(new: float, old: float) -> float:
    return (new / old - 1) * 100


def _entry_index(closes: pd.Series, timestamp: str) -> int:
    """Index of the first close at or after the signal, the first price a follower could trade at.
    US closes are at 16:00 New York time."""
    local = pd.Timestamp(timestamp).tz_localize(LOCAL_TZ)
    ny = local.tz_convert("America/New_York")
    day = pd.Timestamp(ny.date())
    return int(closes.index.searchsorted(day, side="right" if ny.hour >= 16 else "left"))


def _split_factor(rec: dict, entry: float) -> float:
    """Shares today per share held at the signal: quoted price ÷ split-adjusted entry close when they differ
    by a split's worth. Smaller gaps are a stale or intraday quote, not a split."""
    quoted = rec.get("price_at_signal")
    ratio = quoted / entry if quoted else 1
    return 1 if 1 / SPLIT_GAP < ratio < SPLIT_GAP else ratio


def _target(rec: dict, closes: pd.Series, i: int, entry: float, split: float) -> dict | None:
    """Whether the 12-month price target was reached, rescaled through any split since the signal."""
    if not rec.get("price_target"):
        return None
    adjusted = rec["price_target"] / split
    window = closes.iloc[i + 1:i + 1 + TARGET_DAYS]
    up = adjusted >= entry
    reached = window[window >= adjusted] if up else window[window <= adjusted]
    if not reached.empty:
        return {"price": adjusted, "hit": True, "date": reached.index[0].date().isoformat()}
    return {"price": adjusted, "hit": False if len(window) >= TARGET_DAYS else None, "date": None}


def _score(rec: dict, closes: pd.Series | None, bench: pd.Series | None, current: float | None,
           bench_now: float | None) -> dict:
    """Entry, checkpoint returns, return since the signal, the target and (for BUYs) the daily path."""
    out = {"entry_date": None, "entry_price": None, "return_pct": None, "benchmark_pct": None,
           "excess_pct": None, "split_factor": 1, "momentum": None, "checkpoints": [], "target": None, "path": None}
    i = _entry_index(closes, rec["timestamp"]) if closes is not None else 0
    if closes is None or bench is None or i == len(closes) or pd.Timestamp(rec["timestamp"][:10]) < closes.index[0]:
        # No history covering the signal: the return since then from the quoted price, unscored.
        if rec.get("price_at_signal") and current is not None:
            out["return_pct"] = _pct(current, rec["price_at_signal"])
        return out
    entry_day = closes.index[i]
    entry = float(closes.iloc[i])
    b_entry = float(bench.asof(entry_day))
    split = _split_factor(rec, entry)
    out.update(entry_date=entry_day.date().isoformat(), entry_price=entry, split_factor=split)
    if i >= 252:
        # 12-1 month momentum as of the entry: the year's return, skipping the latest month.
        out["momentum"] = float(closes.iloc[i - 21] / closes.iloc[i - 252] - 1)

    for days, label in CHECKPOINTS.items():
        point = {"days": days, "label": label, "date": None, "stock": None, "benchmark": None, "excess": None}
        if i + days < len(closes):
            day = closes.index[i + days]
            stock, b = _pct(float(closes.iloc[i + days]), entry), _pct(float(bench.asof(day)), b_entry)
            point.update(date=day.date().isoformat(), stock=stock, benchmark=b, excess=stock - b)
        out["checkpoints"].append(point)

    now = current if current is not None else float(closes.iloc[-1])
    b_now = bench_now if bench_now is not None else float(bench.iloc[-1])
    out["return_pct"], out["benchmark_pct"] = _pct(now, entry), _pct(b_now, b_entry)
    out["excess_pct"] = out["return_pct"] - out["benchmark_pct"]
    out["target"] = _target(rec, closes, i, entry, split)

    if rec.get("recommendation") == "BUY":
        # Growth of 1 in the stock and in the benchmark from the entry close, for the "follow every BUY" curve.
        held = closes.iloc[i:]
        path = [[d.date().isoformat(), float(c) / entry, float(bench.asof(d)) / b_entry] for d, c in held.items()]
        today = date.today().isoformat()
        if current is not None and path[-1][0] < today:
            path.append([today, now / entry, b_now / b_entry])
        out["path"] = path
    return out


def rule_calls(signal: dict, rule_inputs: dict | None) -> dict:
    """What each simple rule would have said at the same moment; None when it lacks the data.
    Analyst and app-score data were only saved from prompt version 2 on."""
    ri = rule_inputs or {}
    mom, score = signal["momentum"], ri.get("app_score")
    return {
        "always_buy": "BUY",
        "momentum": None if mom is None else "BUY" if mom > 0 else "SELL",
        "analyst": _ANALYST.get(ri.get("analyst")),
        "app_score": None if score is None else "BUY" if score >= APP_SCORE_BUY else "SELL" if score <= APP_SCORE_SELL else "HOLD",
    }


def _tally(pairs: list[tuple[str | None, float | None]]) -> dict:
    """Win rate and average directional return of (call, excess) pairs; HOLDs and missing calls are skipped."""
    results = [_outcome(call, excess) for call, excess in pairs if call in ("BUY", "SELL")]
    wins = sum(o == "Correct" for _, o in results)
    losses = sum(o == "Wrong" for _, o in results)
    returns = [r for r, _ in results]
    return {
        "calls": len(results),
        "win_rate": wins / (wins + losses) * 100 if wins + losses else None,
        "avg_return": sum(returns) / len(returns) if returns else None,
    }


def compare_rules(signals: list[dict]) -> dict:
    """The AI against each simple rule, on the AI's calls that have reached the scoring checkpoint."""
    ready = [s for s in signals if s["score_excess"] is not None]
    rows = [{"key": "ai", "label": "AI", **_tally([(s["recommendation"], s["score_excess"]) for s in ready])}]
    rows += [{"key": k, "label": label, **_tally([(s["rules"][k], s["score_excess"]) for s in ready])}
             for k, label in RULES.items()]
    return {"checked": len(ready), "rows": rows}


def compare_models(signals: list[dict]) -> dict:
    """Each model's calls past the checkpoint; and, on comparison runs where both models assessed the
    same stock from the same context, how often they agreed and how each did on those pairs."""
    ready = [s for s in signals if s["score_excess"] is not None]
    models = sorted({s["model"] for s in signals})

    def rows(subset: list[dict], among: list[dict]) -> list[dict]:
        return [{"model": m, **_tally([(s["recommendation"], s["score_excess"]) for s in subset if s["model"] == m])}
                for m in sorted({s["model"] for s in among})]

    by_key: dict[tuple, list[dict]] = {}
    for s in signals:
        if s["run"]:
            by_key.setdefault((s["run"], s["symbol"]), []).append(s)
    pairs = [g for g in by_key.values() if len({s["provider"] for s in g}) > 1]
    agree = sum(len({s["recommendation"] for s in g}) == 1 for g in pairs)
    ready_pairs = [s for g in pairs for s in g if s["score_excess"] is not None]
    return {
        "models": models,
        "all": rows(ready, signals),
        "pairs": len(pairs),
        "agreement": agree / len(pairs) * 100 if pairs else None,
        "paired": rows(ready_pairs, [s for g in pairs for s in g]),
        "pairs_checked": len(ready_pairs) // 2,
    }


def horizon_days(rec: dict, horizon: int | str) -> int:
    """Trading days to score a call at: a fixed checkpoint, or the horizon the call itself stated."""
    if horizon == "stated":
        return STATED_DAYS.get(rec.get("time_horizon"), 252)
    return int(horizon)


def excess_at(signal: dict, days: int) -> float | None:
    """Stock minus S&P 500 at ``days`` trading days; None until then. A Long-term call's stated
    horizon is beyond the checkpoints, so it stays None."""
    point = next((p for p in signal["checkpoints"] if p["days"] == days), None)
    return point["excess"] if point else None


def scored(signal: dict, days: int) -> tuple[float | None, str]:
    """Directional excess return and outcome at ``days`` trading days, Pending until then."""
    return _outcome(signal["recommendation"], excess_at(signal, days))


def build(username: str, horizon: int | str = 21) -> dict:
    history = load_history(username)
    symbols = sorted({h["symbol"] for h in history})
    tickers = symbols + [BENCHMARK]
    with ThreadPoolExecutor(max_workers=8) as pool:
        prices = dict(zip(tickers, pool.map(market.price, tickers)))
        closes = dict(zip(tickers, pool.map(market.raw_closes, tickers)))

    signals = []
    for i, h in enumerate(history):
        rec = h.get("recommendation", "HOLD")
        s = {
            "id": i,
            "timestamp": h["timestamp"],
            "symbol": h["symbol"],
            "recommendation": rec,
            "confidence": h.get("confidence"),
            "price_at_signal": h.get("price_at_signal"),
            "current_price": prices.get(h["symbol"]),
            "price_target": h.get("price_target"),
            "time_horizon": h.get("time_horizon"),
            **_score(h, closes.get(h["symbol"]), closes.get(BENCHMARK), prices.get(h["symbol"]), prices.get(BENCHMARK)),
            "strengths": h.get("strengths", []),
            "risks": h.get("risks", []),
            "reasoning": h.get("reasoning", ""),
            "steps": h.get("steps", []),
            "position_advice": h.get("position_advice"),
            "portfolio_context": h.get("portfolio_context"),
            "evaluation": h.get("evaluation"),
            # Calls saved before the model was recorded all came from Gemini.
            "model": h.get("model") or "Gemini (model not recorded)",
            "provider": h.get("provider", "gemini"),
            "source": h.get("source", "manual"),
            "run": h.get("run"),
            "prompt_version": h.get("prompt_version", 1),
            "quote_date": h.get("quote_date"),
        }
        days = horizon_days(h, horizon)
        ret, outcome = scored(s, days)
        s.update(score_days=days, score_excess=excess_at(s, days), score_return=ret, outcome=outcome,
                 rules=rule_calls(s, h.get("rule_inputs")))
        signals.append(s)
    signals.sort(key=lambda s: s["timestamp"], reverse=True)
    return {
        "signals": signals,
        "symbols": symbols,
        "horizon": horizon,
        "flat_band": FLAT_BAND,
        "benchmark_available": closes.get(BENCHMARK) is not None,
        "calibration": calibration(signals),
        "rules": compare_rules(signals),
        "models": compare_models(signals),
    }


def _brier(pairs: list[tuple[float, bool]]) -> float | None:
    """Mean squared gap between confidence (n/10, read as the chance the call is right) and the outcome."""
    return sum((c / 10 - right) ** 2 for c, right in pairs) / len(pairs) if pairs else None


def calibration(signals: list[dict]) -> dict:
    """Whether the evaluation's verdicts and lowered confidence line up with how scored calls turned out.

    Only BUY and SELL calls that beat or lagged the benchmark count (draws and pending calls don't).
    Each verdict group gets a win rate and average return vs the benchmark; for evaluated calls, the
    Brier score of the original confidence is set against the adjusted one (lower is better). If
    lowering confidence was warranted, the adjusted score is lower.
    """
    scored_ = [s for s in signals if s["outcome"] in ("Correct", "Wrong")]
    groups = []
    for verdict in ("stands", "weakened", "contradicted", None):
        rows = [s for s in scored_ if (s["evaluation"] or {}).get("verdict") == verdict]
        right = sum(s["outcome"] == "Correct" for s in rows)
        returns = [s["score_return"] for s in rows if s["score_return"] is not None]
        groups.append({
            "verdict": verdict or "not_evaluated",
            "n": len(rows),
            "win_rate": right / len(rows) * 100 if rows else None,
            "avg_return": sum(returns) / len(returns) if returns else None,
        })
    pairs = [(s["confidence"], s["evaluation"]["confidence_adjusted"], s["outcome"] == "Correct")
             for s in scored_ if s["evaluation"] and s["confidence"] is not None]
    return {
        "groups": groups,
        "evaluated": len(pairs),
        "lowered": sum(adj < conf for conf, adj, _ in pairs),
        "brier_original": _brier([(conf, right) for conf, _, right in pairs]),
        "brier_adjusted": _brier([(adj, right) for _, adj, right in pairs]),
    }
