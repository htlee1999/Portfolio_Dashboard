"""Gemini API usage log (data/gemini_usage.json), summaries, and the guard that keeps Gemini calls
inside the free tier's three limits."""

import os
import threading
import time
from collections import deque
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from .storage import data_path, load_json, save_json

# USD per 1K tokens on the paid tier (thinking tokens count as output). Update when pricing changes.
# https://ai.google.dev/gemini-api/docs/pricing (checked Oct 2026)
PRICING = {
    "gemini-3.5-flash-lite": {"input": 0.0003, "output": 0.0025},
    "gemini-2.5-flash": {"input": 0.0003, "output": 0.0025},
}
# Gemini's three limits, per Google Cloud project (every key in it shares them): requests per minute,
# tokens per minute and requests per day. Free-tier values for gemini-3.5-flash-lite, from AI Studio's
# rate-limit page (aistudio.google.com/rate-limit, Oct 2026); Google no longer lists them in its docs.
# Override with GEMINI_RPM / GEMINI_TPM / GEMINI_RPD in .env on a paid tier.
RATE_LIMITS = {
    "rpm": int(os.getenv("GEMINI_RPM", 15)),
    "tpm": int(os.getenv("GEMINI_TPM", 250_000)),
    "rpd": int(os.getenv("GEMINI_RPD", 500)),
}
# The daily count resets at midnight Pacific time, not local midnight.
QUOTA_TZ = ZoneInfo("America/Los_Angeles")
# How long a call waits for room under the per-minute limits before giving up.
MAX_WAIT = 65

_lock = threading.Lock()
# Requests this process has started in the last minute, as (time, tokens). They count before they're
# logged, so concurrent calls can't all squeeze into the same slot.
_started: deque[tuple[float, int]] = deque()
_gate = threading.Lock()


class QuotaExceeded(RuntimeError):
    """A Gemini call refused before it was sent, because it would go over a limit."""


def _path() -> str:
    return data_path("gemini_usage.json")


def _records() -> list[dict]:
    return load_json(_path(), [])


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def log_call(model: str, prompt: str, response: str, operation: str,
             symbol: str | None = None, success: bool = True, error_message: str | None = None,
             input_tokens: int | None = None, output_tokens: int | None = None,
             requests: int | None = None) -> None:
    """``requests`` is how many API requests the call made (a chat answer can take several); by
    default 1, or 0 for a call that a rate limit stopped before it reached the model."""
    if requests is None:
        requests = 0 if not success and _rate_limited(error_message) else 1
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
        "requests": requests,
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


def _rate_limited(error: str | None) -> bool:
    return bool(error) and any(m in error for m in ("429", "RESOURCE_EXHAUSTED", "free-tier limit"))


def _requests(r: dict) -> int:
    # Records from before the field: a 429 used no quota, anything else was one request.
    if "requests" in r:
        return r["requests"]
    return 0 if not r.get("success") and _rate_limited(r.get("error_message")) else 1


def quota_day_start(now: datetime | None = None) -> datetime:
    """The last midnight Pacific, in local time like the log's timestamps."""
    pacific = (now or datetime.now()).astimezone(QUOTA_TZ)
    return pacific.replace(hour=0, minute=0, second=0, microsecond=0).astimezone().replace(tzinfo=None)


def rate_status() -> dict:
    """Gemini usage against each limit. Local-model calls are logged too but don't count."""
    now = datetime.now()
    gemini = [r for r in _records() if str(r.get("model", "")).startswith("gemini")]
    minute = _since(gemini, now - timedelta(minutes=1))
    start = quota_day_start(now)
    return {
        "rpm": sum(_requests(r) for r in minute),
        "tpm": sum(r["total_tokens"] for r in minute),
        "rpd": sum(_requests(r) for r in _since(gemini, start)),
        "limits": RATE_LIMITS,
        "resets_at": (start + timedelta(days=1)).astimezone(QUOTA_TZ).astimezone().replace(tzinfo=None)
        .isoformat(timespec="seconds"),
    }


def requests_left_today() -> int:
    s = rate_status()
    return max(0, s["limits"]["rpd"] - s["rpd"])


def acquire(tokens: int) -> None:
    """Wait until one Gemini request of about ``tokens`` input tokens fits under the per-minute
    limits, and count it. Raises QuotaExceeded when the day's requests are used up, or when the
    minute doesn't clear within MAX_WAIT seconds. Call it right before every Gemini request."""
    deadline = time.monotonic() + MAX_WAIT
    while True:
        with _gate:
            s = rate_status()
            limits = s["limits"]
            if s["rpd"] >= limits["rpd"]:
                resets = datetime.fromisoformat(s["resets_at"])
                raise QuotaExceeded(f"Gemini free-tier limit reached: all {limits['rpd']} requests for today are "
                                    f"used. The quota resets at {resets:%H:%M} (midnight Pacific).")
            now = time.monotonic()
            while _started and _started[0][0] < now - 60:
                _started.popleft()
            # The log covers other processes (the scheduled run); _started covers this one's calls in flight.
            rpm = max(s["rpm"], len(_started))
            tpm = max(s["tpm"], sum(t for _, t in _started))
            if rpm < limits["rpm"] and (tpm + tokens <= limits["tpm"] or not rpm):
                _started.append((now, tokens))
                return
        if time.monotonic() >= deadline:
            which = "requests" if rpm >= limits["rpm"] else "tokens"
            raise QuotaExceeded(f"Gemini free-tier limit reached: {which} per minute are used up. Try again in a minute.")
        time.sleep(2)


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
        "rate": rate_status(),
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
