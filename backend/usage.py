"""Gemini API usage log (data/gemini_usage.json) and summaries."""

import threading
from datetime import datetime, timedelta

from .storage import data_path, load_json, save_json

# USD per 1K tokens. Update when pricing changes.
PRICING = {"gemini-2.5-flash": {"input": 0.000075, "output": 0.0003}}
# Requests per minute / hour, and tokens per day. Adjust to your Gemini plan.
RATE_LIMITS = {"minute": 15, "hour": 900, "day_tokens": 1_000_000}

_lock = threading.Lock()


def _path() -> str:
    return data_path("gemini_usage.json")


def _records() -> list[dict]:
    return load_json(_path(), [])


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def log_call(model: str, prompt: str, response: str, operation: str,
             symbol: str | None = None, success: bool = True, error_message: str | None = None,
             input_tokens: int | None = None, output_tokens: int | None = None) -> None:
    input_tokens = input_tokens if input_tokens is not None else estimate_tokens(prompt)
    output_tokens = output_tokens if output_tokens is not None else (estimate_tokens(response) if success else 0)
    price = PRICING.get(model, {"input": 0.0, "output": 0.0})
    record = {
        "timestamp": datetime.now().isoformat(),
        "model": model,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": input_tokens + output_tokens,
        "cost_usd": input_tokens / 1000 * price["input"] + output_tokens / 1000 * price["output"],
        "operation": operation,
        "symbol": symbol,
        "success": success,
        "error_message": error_message,
    }
    with _lock:
        records = _records()
        records.append(record)
        save_json(_path(), records)


def _since(records: list[dict], cutoff: datetime) -> list[dict]:
    return [r for r in records if datetime.fromisoformat(r["timestamp"]) >= cutoff]


def summary(days: int) -> dict:
    now = datetime.now()
    records = _records()
    recent = _since(records, now - timedelta(days=days))

    def group(key: str) -> list[dict]:
        out: dict[str, dict] = {}
        for r in recent:
            k = r.get(key)
            if not k:
                continue
            g = out.setdefault(k, {"name": k, "calls": 0, "tokens": 0, "cost": 0.0})
            g["calls"] += 1
            g["tokens"] += r["total_tokens"]
            g["cost"] += r["cost_usd"]
        return sorted(out.values(), key=lambda g: -g["calls"])

    daily: dict[str, dict] = {}
    for r in recent:
        d = daily.setdefault(r["timestamp"][:10], {"date": r["timestamp"][:10], "calls": 0, "tokens": 0, "cost": 0.0})
        d["calls"] += 1
        d["tokens"] += r["total_tokens"]
        d["cost"] += r["cost_usd"]

    calls = len(recent)
    ok = sum(1 for r in recent if r.get("success"))
    tokens = sum(r["total_tokens"] for r in recent)
    cost = sum(r["cost_usd"] for r in recent)
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    return {
        "days": days,
        "total_calls": calls,
        "successful_calls": ok,
        "failed_calls": calls - ok,
        "total_tokens": tokens,
        "total_cost": cost,
        "avg_tokens_per_call": tokens / calls if calls else 0,
        "daily": sorted(daily.values(), key=lambda d: d["date"]),
        "operations": group("operation"),
        "symbols": group("symbol"),
        "rate": {
            "minute": len(_since(records, now - timedelta(minutes=1))),
            "hour": len(_since(records, now - timedelta(hours=1))),
            "day_tokens": sum(r["total_tokens"] for r in _since(records, today)),
            "limits": RATE_LIMITS,
        },
        "recent": sorted(recent, key=lambda r: r["timestamp"], reverse=True)[:25],
    }


def clear_older_than(days: int) -> int:
    cutoff = datetime.now() - timedelta(days=days)
    with _lock:
        records = _records()
        kept = _since(records, cutoff)
        save_json(_path(), kept)
    return len(records) - len(kept)


def export_rows(days: int) -> list[dict]:
    return _since(_records(), datetime.now() - timedelta(days=days))
