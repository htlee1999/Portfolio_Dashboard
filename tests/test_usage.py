"""Gemini's three rate limits and the guard in front of every Gemini call. No network.

Run with: PYTHONPATH=. pytest tests
"""

from datetime import datetime, timedelta

import pytest

from backend import usage


@pytest.fixture(autouse=True)
def log(monkeypatch):
    records: list[dict] = []
    monkeypatch.setattr(usage, "_records", lambda: records)
    monkeypatch.setattr(usage, "_started", usage.deque())
    monkeypatch.setattr(usage, "MAX_WAIT", 0)
    monkeypatch.setattr(usage.time, "sleep", lambda s: None)
    monkeypatch.setattr(usage, "RATE_LIMITS", {"rpm": 15, "tpm": 250_000, "rpd": 500})
    return records


def _rec(ago: timedelta, tokens: int = 5000, model: str = "gemini-3.5-flash-lite", **kw) -> dict:
    return {"timestamp": (datetime.now() - ago).isoformat(), "model": model, "total_tokens": tokens,
            "success": True, "error_message": None, **kw}


def test_counts_each_window_and_skips_local_model(log):
    log += [_rec(timedelta(seconds=10)), _rec(timedelta(seconds=20), requests=3),
            _rec(timedelta(minutes=5)), _rec(timedelta(seconds=5), model="qwen3.5:9b")]
    s = usage.rate_status()
    assert s["rpm"] == 4 and s["tpm"] == 10_000
    assert s["rpd"] >= 4  # the 5-minute-old call is today unless midnight Pacific just passed


def test_rate_limited_failures_use_no_quota(log):
    log += [_rec(timedelta(seconds=5), success=False, error_message="429 RESOURCE_EXHAUSTED"),
            _rec(timedelta(seconds=5), success=False, error_message="Gemini free-tier limit reached: ..."),
            _rec(timedelta(seconds=5), success=False, error_message="500 internal")]
    assert usage.rate_status()["rpm"] == 1


def test_day_starts_at_midnight_pacific():
    # 16:00 in Singapore (UTC+8) on 29 Oct 2026 is 01:00 PDT, so the quota day began an hour ago.
    sgt = usage.ZoneInfo("Asia/Singapore")
    now = datetime(2026, 10, 29, 16, 0, tzinfo=sgt)
    start = usage.quota_day_start(now)
    assert now - start.astimezone() == timedelta(hours=1)


def test_acquire_refuses_when_day_used_up(log):
    log += [_rec(timedelta(seconds=1), requests=500)]
    with pytest.raises(usage.QuotaExceeded, match="500 requests for today"):
        usage.acquire(4000)


def test_acquire_waits_out_a_full_minute(log):
    log += [_rec(timedelta(seconds=30)) for _ in range(15)]
    with pytest.raises(usage.QuotaExceeded, match="requests per minute"):
        usage.acquire(4000)


def test_acquire_counts_calls_in_flight():
    for _ in range(15):
        usage.acquire(4000)
    with pytest.raises(usage.QuotaExceeded):
        usage.acquire(4000)


def test_acquire_keeps_under_tokens_per_minute(log):
    log += [_rec(timedelta(seconds=30), tokens=248_000)]
    with pytest.raises(usage.QuotaExceeded, match="tokens per minute"):
        usage.acquire(4000)
    log.clear()
    usage.acquire(300_000)  # one oversized request still goes through on an empty minute
