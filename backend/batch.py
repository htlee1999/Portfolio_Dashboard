"""Scheduled assessments over your holdings and a fixed list of stocks.

The fixed list builds an unbiased track record; your holdings are added so the stocks you own are
assessed every run too. Each call records which it was (``held``, ``in_list``; a stock can be both).

Runs on the local model every time. In the last week of the month it also runs Gemini on the
same context, so the Track Record can compare the two models on identical inputs.

The work is spread out: on run days launchd starts this every hour, and each start assesses the
next few stocks of the day's run and exits, so the Mac is never busy for long.

    PYTHONPATH=. python -m backend.batch                 # what the schedule runs: the next chunk
    PYTHONPATH=. python -m backend.batch --chunk 0       # the rest of today's run in one go
    PYTHONPATH=. python -m backend.batch --mode compare --symbols AAPL KO   # a one-off run
"""

import argparse
import math
import os
import time
from datetime import date, datetime, timedelta

import requests

from config import get_ollama_model, get_ollama_url, is_gemini_api_configured

from . import assessment, mailer, market, usage
from .auth import get_email
from .plan import digest
from .storage import data_path, load_holdings, load_json, save_json

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

# Run days (Monday = 0) and the hours launchd starts a chunk on them. A run is split over the first
# eight hours, so it's done by 16:00; the later hours are slack for chunks missed while the Mac was asleep.
DAYS = (0, 4)
HOURS = range(9, 21)
CHUNKS = 8

# Fewest stocks per chunk; more when holdings make the run too long for CHUNKS chunks.
CHUNK = 4

# Seconds between stocks within a chunk, to let the machine cool off.
PAUSE = 30

# Data fetches per stock. After a Yahoo failure every fetch is skipped for a cooldown, so a retry
# waits that out first; without it one rate-limit fails the next several stocks too.
FETCH_ATTEMPTS = 3

RUNS_LOG = "scheduled_runs.json"
STATUS = "scheduled_status.json"
PLIST = os.path.expanduser("~/Library/LaunchAgents/com.portfolio-dashboard.assessments.plist")


def slots(day: date) -> list[datetime]:
    """When launchd starts a chunk on ``day``; none on other days."""
    if day.weekday() not in DAYS:
        return []
    return [datetime.combine(day, datetime.min.time()).replace(hour=h) for h in HOURS]


def next_slot(now: datetime) -> datetime:
    """The next time launchd starts a chunk."""
    for offset in range(8):
        for at in slots(now.date() + timedelta(days=offset)):
            if at > now:
                return at
    raise AssertionError("DAYS is empty")


def next_run(now: datetime) -> datetime:
    """When the next day's run starts: the first slot of a run day, after ``now``."""
    for offset in range(8):
        day = slots(now.date() + timedelta(days=offset))
        if day and day[0] > now:
            return day[0]
    raise AssertionError("DAYS is empty")


def held_symbols(username: str) -> list[str]:
    """Stocks in the portfolio now, in the order first bought."""
    return list(dict.fromkeys(h["Symbol"].upper() for h in load_holdings(username) if h.get("Symbol") and (h.get("Quantity") or 0) > 0))


def plan(username: str) -> tuple[list[str], list[str]]:
    """A run's stocks, your holdings first, then the rest of the fixed list; and which are held."""
    held = held_symbols(username)
    return held + [s for s in UNIVERSE if s not in held], held


def chunk_size(total: int) -> int:
    return max(CHUNK, math.ceil(total / CHUNKS))


def _email_alerts(username: str, entry: dict) -> None:
    """At the start of a day's run, email what needs attention (when SMTP and an email are set up)."""
    try:
        text = digest(username, load_json(data_path("settings.json"), {}).get("base_currency", "USD"))
        if text and mailer.send_alerts(username, get_email(username), text):
            entry["alerts_emailed"] = True
    except Exception as e:
        entry["skipped"].append(f"alert email: {e}")


def _alive(pid: int | None) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except (TypeError, ProcessLookupError):
        return False
    except PermissionError:
        return True


def status(now: datetime | None = None) -> dict | None:
    """The current or last run's progress. ``state`` is running (a chunk is being assessed),
    waiting (more chunks are due later today), finished, or incomplete (the day's slots ran out)."""
    now = now or datetime.now()
    s = load_json(data_path(STATUS), None)
    if not s:
        return None
    if s.get("active") and _alive(s.get("pid")):
        s["state"] = "running"
    elif s.get("finished"):
        s["state"] = "finished"
    elif s["run"] == now.date().isoformat() and any(at > now for at in slots(now.date())):
        s["state"] = "waiting"
        s["next_chunk"] = next_slot(now).isoformat()
    else:
        s["state"] = "incomplete"
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


def _attempted(entry: dict) -> set[str]:
    return {r["symbol"] for r in entry["ok"] + entry["failed"]}


def run(username: str, mode: str = "auto", symbols: list[str] | None = None, chunk: int | None = None) -> dict:
    """Assess the next ``chunk`` stocks of today's run (0: all that are left; None: the run's chunk
    size), starting the run if there isn't one. With ``symbols``, a one-off run of just those, all at once."""
    now = datetime.now()
    if symbols:
        chunk = 0
    path = data_path(RUNS_LOG)
    runs = load_json(path, [])
    run_id = now.strftime("%Y-%m-%dT%H:%M") if symbols else now.date().isoformat()
    entry = next((r for r in runs if r["run"] == run_id and r.get("user", "admin") == username), None)
    if entry is None:
        # Which models and stocks run is fixed when the day's run starts, so every chunk of it matches.
        planned, held = plan(username)
        entry = {"user": username, "run": run_id, "started": now.isoformat(), "finished": None,
                 "providers": providers_for(mode, now.date()), "symbols": symbols or planned, "held": held,
                 "skipped": [], "ok": [], "failed": []}
        runs.append(entry)
        if not symbols:
            _email_alerts(username, entry)
    elif entry["finished"]:
        # Later hours of a finished day have nothing to do.
        return {**entry, "assessed": []}

    def save() -> None:
        save_json(path, runs[-200:])

    providers = list(entry["providers"])
    if "local" in providers and (problem := local_ready()):
        providers.remove("local")
        entry["skipped"].append(f"local: {problem} ({now:%H:%M})")
    if "gemini" in providers and not is_gemini_api_configured():
        providers.remove("gemini")
        entry["skipped"].append(f"gemini: GEMINI_API_KEY is not configured ({now:%H:%M})")
    elif "gemini" in providers and usage.requests_left_today() == 0:
        # Its stocks wait for a later hour; the quota resets at midnight Pacific.
        providers.remove("gemini")
        entry["skipped"].append(f"gemini: today's free-tier requests are used up ({now:%H:%M})")
    if chunk is None:
        chunk = chunk_size(len(entry["symbols"]))
    held = set(entry.get("held", []))
    remaining = [s for s in entry["symbols"] if s not in _attempted(entry)]
    # A model that can't run leaves its stocks for a later chunk rather than marking them failed.
    todo = remaining[:chunk or None] if providers == entry["providers"] else []

    progress = {"user": username, "run": run_id, "pid": os.getpid(), "started": entry["started"], "providers": entry["providers"],
                "total": len(entry["symbols"]), "held": len(held & set(entry["symbols"])), "done": len(_attempted(entry)), "current": None,
                "ok": len(entry["ok"]), "failed": len(entry["failed"]), "finished": entry["finished"], "active": bool(todo)}
    _save_status(progress)
    save()

    for n, symbol in enumerate(todo):
        if n:
            time.sleep(PAUSE)
        progress["current"] = symbol
        _save_status(progress)
        try:
            ctx = _context(username, symbol)
        except Exception as e:
            entry["failed"].append({"symbol": symbol, "provider": None, "error": str(e)})
        else:
            # Both models get the identical context, so a comparison week differs only in the model.
            for provider in providers:
                try:
                    out = assessment.generate(username, ctx, provider, source="scheduled", run=run_id,
                                              held=symbol in held, in_list=symbol in UNIVERSE)
                    entry["ok"].append({"symbol": symbol, "provider": provider, "recommendation": out["recommendation"]})
                except Exception as e:
                    entry["failed"].append({"symbol": symbol, "provider": provider, "error": str(e)})
        save()
        progress.update(done=len(_attempted(entry)), ok=len(entry["ok"]), failed=len(entry["failed"]))
        print(f"{symbol}: " + ", ".join(f"{r['provider']} {r.get('recommendation') or 'failed'}"
                                       for r in entry["ok"] + entry["failed"] if r["symbol"] == symbol), flush=True)

    if not entry["finished"] and not [s for s in entry["symbols"] if s not in _attempted(entry)]:
        entry["finished"] = datetime.now().isoformat()
        save()
    _save_status({**progress, "current": None, "finished": entry["finished"], "active": False})
    return {**entry, "assessed": todo}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--user", default="admin", help="whose history the calls are saved to (default admin)")
    parser.add_argument("--mode", choices=["auto", "local", "gemini", "compare"], default="auto",
                        help="auto: local, plus Gemini in the last week of the month (set when the day's run starts)")
    parser.add_argument("--chunk", type=int, help=f"stocks to assess now (default the run's chunk size, at least {CHUNK}; 0 for all left)")
    parser.add_argument("--symbols", nargs="+", help="a one-off run of just these stocks")
    parser.add_argument("--print-slots", action="store_true", help=argparse.SUPPRESS)  # for schedule.sh
    args = parser.parse_args()
    if args.print_slots:
        # launchd's Weekday counts Sunday as 0.
        for weekday in DAYS:
            for hour in HOURS:
                print((weekday + 1) % 7, hour)
        return
    r = run(args.user, args.mode, args.symbols, args.chunk)
    left = len([s for s in r["symbols"] if s not in _attempted(r)])
    print(f"Run {r['run']}: assessed {len(r['assessed'])} now; {len(r['ok'])} calls saved, {len(r['failed'])} failed, "
          f"{left} stocks left" + (f"; skipped {'; '.join(r['skipped'][-2:])}" if r["skipped"] else ""))


if __name__ == "__main__":
    main()
