"""Scheduled assessments over a fixed list of stocks, to build an unbiased track record.

Runs on the local model every time. In the last week of the month it also runs Gemini on the
same context, so the Track Record can compare the two models on identical inputs.

    PYTHONPATH=. python -m backend.batch                 # what the schedule runs
    PYTHONPATH=. python -m backend.batch --mode compare --symbols AAPL KO
"""

import argparse
import os
import time
from datetime import date, datetime, timedelta

import requests

from config import get_ollama_model, get_ollama_url, is_gemini_api_configured

from . import assessment, market
from .storage import data_path, load_json, save_json

# A fixed spread across sectors, the same every run, so the record isn't tilted towards stocks you
# already like. Edit freely; a change only affects runs from then on.
UNIVERSE = [
    "AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "AMD", "INTC", "CRM",  # technology
    "JPM", "BAC", "V",  # financials
    "UNH", "JNJ", "LLY", "PFE",  # health care
    "PG", "KO", "PEP", "WMT", "COST", "NKE",  # consumer
    "XOM", "CVX",  # energy
    "CAT", "BA",  # industrials
    "HD", "DIS", "NFLX", "TSLA",  # consumer discretionary and media
]

# Data fetches per stock. After a Yahoo failure every fetch is skipped for a cooldown, so a retry
# waits that out first; without it one rate-limit fails the next several stocks too.
FETCH_ATTEMPTS = 3

# Gemini's free tier allows 15 requests a minute; stay under it.
GEMINI_RPM = 12

RUNS_LOG = "scheduled_runs.json"
STATUS = "scheduled_status.json"

# When launchd starts a run (weekday, Monday = 0; hour). Keep in step with schedule.sh.
SCHEDULE = [(0, 9), (4, 9)]
PLIST = os.path.expanduser("~/Library/LaunchAgents/com.portfolio-dashboard.assessments.plist")


def next_run(now: datetime) -> datetime:
    day = now.replace(minute=0, second=0, microsecond=0)
    for offset in range(8):
        d = day + timedelta(days=offset)
        for weekday, hour in SCHEDULE:
            at = d.replace(hour=hour)
            if d.weekday() == weekday and at > now:
                return at
    raise AssertionError("SCHEDULE is empty")


def _alive(pid: int | None) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except (TypeError, ProcessLookupError):
        return False
    except PermissionError:
        return True


def status() -> dict:
    """The current or last run's progress; ``state`` is running, finished or interrupted (the process
    died before finishing)."""
    s = load_json(data_path(STATUS), None)
    if s and not s.get("finished"):
        s["state"] = "running" if _alive(s.get("pid")) else "interrupted"
    elif s:
        s["state"] = "finished"
    return s


def _save_status(s: dict) -> None:
    save_json(data_path(STATUS), s)


def is_last_week(day: date) -> bool:
    """The last seven days of the month."""
    return (day + timedelta(days=7)).month != day.month


def providers_for(mode: str, day: date) -> list[str]:
    if mode == "auto":
        mode = "compare" if is_last_week(day) else "local"
    return ["local", "gemini"] if mode == "compare" else [mode]


def local_ready() -> str | None:
    """None when Ollama is up and has the model; otherwise what's wrong."""
    try:
        tags = requests.get(f"{get_ollama_url()}/api/tags", timeout=5).json()
    except requests.RequestException:
        return f"Ollama isn't running at {get_ollama_url()}"
    if get_ollama_model() not in {m["name"] for m in tags.get("models", [])}:
        return f"model {get_ollama_model()} isn't pulled (ollama pull {get_ollama_model()})"
    return None


def _context(username: str, symbol: str) -> dict:
    for attempt in range(FETCH_ATTEMPTS):
        try:
            # No position and no news: the call rests on the same kinds of data every run.
            return assessment.build_context(username, symbol, "1y", include_sentiment=False, include_position=False)
        except LookupError:
            if attempt == FETCH_ATTEMPTS - 1:
                raise
            print(f"{symbol}: no data, retrying after Yahoo's cooldown", flush=True)
            time.sleep(market.yahoo_wait() + 30)
    raise AssertionError("unreachable")


def run(username: str, mode: str = "auto", symbols: list[str] | None = None) -> dict:
    started = datetime.now()
    providers = providers_for(mode, started.date())
    skipped = []
    if "local" in providers and (problem := local_ready()):
        providers.remove("local")
        skipped.append(f"local: {problem}")
    if "gemini" in providers and not is_gemini_api_configured():
        providers.remove("gemini")
        skipped.append("gemini: GEMINI_API_KEY is not configured")

    run_id = started.strftime("%Y-%m-%dT%H:%M")
    results = {"user": username, "run": run_id, "started": started.isoformat(), "providers": providers, "skipped": skipped,
               "ok": [], "failed": []}
    todo = (symbols or UNIVERSE) if providers else []
    progress = {"user": username, "run": run_id, "pid": os.getpid(), "started": started.isoformat(), "providers": providers,
                "total": len(todo), "done": 0, "current": None, "ok": 0, "failed": 0, "finished": None}
    _save_status(progress)
    last_gemini = 0.0
    for symbol in todo:
        progress["current"] = symbol
        _save_status(progress)
        try:
            ctx = _context(username, symbol)
        except Exception as e:
            results["failed"].append({"symbol": symbol, "provider": None, "error": str(e)})
            progress.update(done=progress["done"] + 1, failed=len(results["failed"]))
            continue
        # Both models get the identical context, so a comparison week differs only in the model.
        for provider in providers:
            if provider == "gemini":
                time.sleep(max(0.0, last_gemini + 60 / GEMINI_RPM - time.time()))
                last_gemini = time.time()
            try:
                out = assessment.generate(username, ctx, provider, source="scheduled", run=run_id)
                results["ok"].append({"symbol": symbol, "provider": provider, "recommendation": out["recommendation"]})
            except Exception as e:
                results["failed"].append({"symbol": symbol, "provider": provider, "error": str(e)})
        progress.update(done=progress["done"] + 1, ok=len(results["ok"]), failed=len(results["failed"]))
        print(f"{symbol}: " + ", ".join(f"{r['provider']} {r.get('recommendation') or 'failed'}"
                                       for r in results["ok"] + results["failed"] if r["symbol"] == symbol), flush=True)

    results["finished"] = datetime.now().isoformat()
    _save_status({**progress, "current": None, "finished": results["finished"]})
    path = data_path(RUNS_LOG)
    save_json(path, (load_json(path, []) + [results])[-200:])
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--user", default="admin", help="whose history the calls are saved to (default admin)")
    parser.add_argument("--mode", choices=["auto", "local", "gemini", "compare"], default="auto",
                        help="auto: local, plus Gemini in the last week of the month")
    parser.add_argument("--symbols", nargs="+", help="override the stock list")
    args = parser.parse_args()
    r = run(args.user, args.mode, args.symbols)
    print(f"Run {r['run']}: {len(r['ok'])} calls saved, {len(r['failed'])} failed"
          + (f"; skipped {'; '.join(r['skipped'])}" if r["skipped"] else ""))


if __name__ == "__main__":
    main()
