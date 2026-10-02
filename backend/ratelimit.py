"""In-memory sliding-window limits for sign-in, sign-up and other password checks.

Counts live in the API process, so each server instance keeps its own. That is enough
to stop password guessing against a single long-running server. Behind several instances
(e.g. serverless), put a shared limit in front as well (Vercel Firewall, Cloudflare, ...).
"""

import os
import threading
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request

_hits: dict[str, deque[float]] = defaultdict(deque)
_lock = threading.Lock()


def client_ip(request: Request) -> str:
    """The caller's IP. Proxy headers are trusted only with TRUST_PROXY=1, since anyone can send them."""
    if os.getenv("TRUST_PROXY") == "1":
        forwarded = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
        if forwarded:
            return forwarded
    return request.client.host if request.client else "unknown"


def _prune(key: str, window: int, now: float) -> deque[float]:
    hits = _hits[key]
    while hits and hits[0] <= now - window:
        hits.popleft()
    return hits


def check(key: str, limit: int, window: int) -> None:
    """Raise 429 if `key` already has `limit` hits inside the last `window` seconds."""
    now = time.time()
    with _lock:
        hits = _prune(key, window, now)
        if len(hits) >= limit:
            retry = int(hits[0] + window - now) + 1
            minutes = max(1, round(retry / 60))
            raise HTTPException(
                429, f"Too many attempts. Try again in {minutes} minute{'s' if minutes != 1 else ''}.",
                headers={"Retry-After": str(retry)},
            )


def hit(key: str) -> None:
    with _lock:
        _hits[key].append(time.time())
        if len(_hits) > 50_000:  # keep memory bounded under a flood of distinct keys
            cutoff = time.time() - 24 * 3600
            for k in [k for k, v in _hits.items() if not v or v[-1] < cutoff]:
                del _hits[k]


def reset(key: str) -> None:
    with _lock:
        _hits.pop(key, None)
