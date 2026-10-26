"""Planetary retrograde calendar, cross-checked across three independent ephemerides.

A planet is retrograde while its apparent geocentric ecliptic longitude decreases. Each
source supplies one longitude per day; a station is where the daily motion changes sign,
timed to the minute by fitting a parabola through the three samples around the turn.

Sources (all free, no key):
- NASA JPL Horizons API: DE441 numerical integration (the reference).
- Swiss Ephemeris through astro.com's swetest service: the ephemeris most retrograde tables use.
- Astronomy Engine, computed locally: VSOP87 planetary theory, so it works offline too.

Each station is matched across sources. A period is "verified" when every available source
agrees within ``AGREE_HOURS``. Results are cached in ``data/`` because ephemerides don't change.
"""

import logging
import math
import re
import statistics
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone

import requests

from .storage import data_path, load_json, save_json

log = logging.getLogger(__name__)

# (id, name, JPL Horizons id, swetest planet code)
PLANETS = [
    ("mercury", "Mercury", "199", "2"),
    ("venus", "Venus", "299", "3"),
    ("mars", "Mars", "499", "4"),
    ("jupiter", "Jupiter", "599", "5"),
    ("saturn", "Saturn", "699", "6"),
    ("uranus", "Uranus", "799", "7"),
    ("neptune", "Neptune", "899", "8"),
    ("pluto", "Pluto", "999", "9"),
]
SIGNS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
         "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]

SOURCES = {
    "horizons": {"name": "NASA JPL Horizons", "method": "DE441 numerical integration (API)",
                 "url": "https://ssd.jpl.nasa.gov/horizons/"},
    "swisseph": {"name": "Swiss Ephemeris", "method": "astro.com swetest service (API)",
                 "url": "https://www.astro.com/swisseph/"},
    "local": {"name": "Astronomy Engine", "method": "VSOP87 theory, computed on this server",
              "url": "https://github.com/cosinekitty/astronomy"},
}

# Outer-planet shadows run months before and after the retrograde itself.
BUFFER_DAYS = 400
AGREE_HOURS = 12.0          # sources within this of each other count as agreeing
MATCH_DAYS = 5.0            # stations further apart than this are different stations
CACHE_OK = 30 * 86400       # all sources answered
CACHE_PARTIAL = 3600        # retry a failed source after an hour
MIN_YEAR, MAX_YEAR, MAX_SPAN = 1950, 2100, 5
_UA = {"User-Agent": "Mozilla/5.0 (Portfolio Dashboard retrograde calendar)"}


# ── Sources: each returns {planet_id: [longitude per day from start]} ─────────

_HZ_ROW = re.compile(r"^\s*\d{4}-[A-Za-z]{3}-\d{2} \d{2}:\d{2}\s+([\d.]+)\s+(-?[\d.]+)")


def _horizons_planet(code: str, start: date, days: int) -> list[float]:
    params = {
        "format": "json", "COMMAND": f"'{code}'", "OBJ_DATA": "'NO'", "MAKE_EPHEM": "'YES'",
        "EPHEM_TYPE": "'OBSERVER'", "CENTER": "'500@399'", "QUANTITIES": "'31'",
        "START_TIME": f"'{start.isoformat()}'",
        "STOP_TIME": f"'{(start + timedelta(days=days - 1)).isoformat()}'", "STEP_SIZE": "'1 d'",
    }
    for attempt in range(4):
        r = requests.get("https://ssd.jpl.nasa.gov/api/horizons.api", params=params, timeout=60)
        if r.status_code != 503 or attempt == 3:
            break
        time.sleep(2 * (attempt + 1))  # Horizons sheds load with 503s; back off and retry
    r.raise_for_status()
    text = r.json().get("result", "")
    body = text.split("$$SOE", 1)[-1].split("$$EOE", 1)[0]
    lons = [float(m.group(1)) for line in body.splitlines() if (m := _HZ_ROW.match(line))]
    if len(lons) != days:
        raise ValueError(f"Horizons returned {len(lons)} of {days} days")
    return lons


def fetch_horizons(start: date, days: int) -> dict[str, list[float]]:
    # One planet at a time: Horizons answers concurrent requests from one client with 503s.
    return {pid: _horizons_planet(code, start, days) for pid, _, code, _ in PLANETS}


def fetch_swisseph(start: date, days: int) -> dict[str, list[float]]:
    # One request for every planet. Times are 0h TT, about 69 s before 0h UT: under a
    # thousandth of a degree, which the station fit doesn't notice.
    params = {"b": f"{start.day}.{start.month}.{start.year}", "n": str(days), "s": "1",
              "p": "".join(code for *_, code in PLANETS), "e": "-eswe", "f": "PTls", "arg": ""}
    r = requests.get("https://www.astro.com/cgi/swetest.cgi", params=params, headers=_UA, timeout=90)
    r.raise_for_status()
    text = re.sub(r"<[^>]*>", "", r.text)
    out: dict[str, list[float]] = {pid: [] for pid, *_ in PLANETS}
    names = {name: pid for pid, name, *_ in PLANETS}
    for line in text.splitlines():
        parts = line.split()
        if len(parts) >= 3 and parts[0] in names and re.fullmatch(r"\d{2}\.\d{2}\.\d{4}", parts[1]):
            out[names[parts[0]]].append(float(parts[2]))
    for pid, lons in out.items():
        if len(lons) != days:
            raise ValueError(f"swetest returned {len(lons)} of {days} days for {pid}")
    return out


def compute_local(start: date, days: int) -> dict[str, list[float]]:
    import astronomy

    t0 = astronomy.Time.Make(start.year, start.month, start.day, 0, 0, 0)
    out = {}
    for pid, name, *_ in PLANETS:
        body = getattr(astronomy.Body, name)
        out[pid] = [astronomy.Ecliptic(astronomy.GeoVector(body, t0.AddDays(i), True)).elon for i in range(days)]
    return out


_FETCHERS = {"horizons": fetch_horizons, "swisseph": fetch_swisseph, "local": compute_local}


# ── Station detection ────────────────────────────────────────────────────────

def _unwrap(lons: list[float]) -> list[float]:
    out = [lons[0]]
    for lon in lons[1:]:
        d = (lon - out[-1] + 180) % 360 - 180
        out.append(out[-1] + d)
    return out


def find_stations(lons: list[float]) -> list[dict]:
    """Turning points of the longitude series: kind "R" (turns retrograde) or "D" (turns direct)."""
    u = _unwrap(lons)
    stations = []
    for i in range(1, len(u) - 1):
        before, after = u[i] - u[i - 1], u[i + 1] - u[i]
        if before > 0 >= after or before < 0 <= after:
            y0, y1, y2 = u[i - 1], u[i], u[i + 1]
            curve = y0 - 2 * y1 + y2
            offset = 0.5 * (y0 - y2) / curve if curve else 0.0
            offset = max(-1.0, min(1.0, offset))
            lon = y1 + 0.25 * (y2 - y0) * offset + 0.5 * curve * offset * offset
            stations.append({"kind": "R" if before > 0 else "D", "day": i + offset, "lon": lon})
    return stations


def _crossing(u: list[float], target: float, lo: int, hi: int, step: int) -> float | None:
    """First day (fractional) walking from ``lo`` toward ``hi`` where the series crosses ``target``."""
    i = lo
    while 0 <= i + step < len(u) and (i < hi if step > 0 else i > hi):
        a, b = u[i], u[i + step]
        if (a - target) * (b - target) <= 0 and a != b:
            return i + step * (target - a) / (b - a)
        i += step
    return None


def _periods(lons: list[float]) -> list[dict]:
    """Retrograde periods (station R to the next station D) with their shadow phases."""
    u = _unwrap(lons)
    stations = find_stations(lons)
    out = []
    for s, nxt in zip(stations, stations[1:]):
        if s["kind"] != "R" or nxt["kind"] != "D":
            continue
        # Shadow: the stretch of sky the retrograde re-covers. It opens when the planet first
        # reaches the longitude where it will station direct, and closes when it gets back
        # to the longitude where it stationed retrograde.
        r_lon, d_lon = s["lon"], nxt["lon"]  # both on the same unwrapped scale as u
        pre = _crossing(u, d_lon, math.floor(s["day"]), 0, -1)
        post = _crossing(u, r_lon, math.ceil(nxt["day"]), len(u) - 1, 1)
        out.append({"r": s, "d": nxt, "shadow_start": pre, "shadow_end": post})
    return out


# ── Assembly ─────────────────────────────────────────────────────────────────

def _iso(start: date, day: float | None) -> str | None:
    if day is None:
        return None
    t = datetime(start.year, start.month, start.day, tzinfo=timezone.utc) + timedelta(days=day)
    return t.replace(second=0, microsecond=0).isoformat().replace("+00:00", "Z")


def _sign(lon: float) -> dict:
    lon %= 360
    return {"sign": SIGNS[int(lon // 30)], "degree": round(lon % 30, 2), "longitude": round(lon, 4)}


def _match(day: float, kind: str, candidates: list[dict]) -> dict | None:
    best = min((c for c in candidates if c["kind"] == kind), key=lambda c: abs(c["day"] - day), default=None)
    return best if best and abs(best["day"] - day) <= MATCH_DAYS else None


def build(start_year: int, end_year: int) -> dict:
    lo, hi = date(start_year, 1, 1), date(end_year, 12, 31)
    start = lo - timedelta(days=BUFFER_DAYS)
    days = (hi - start).days + BUFFER_DAYS + 1

    data: dict[str, dict] = {}
    sources = []
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {sid: pool.submit(fn, start, days) for sid, fn in _FETCHERS.items()}
        for sid, fut in futures.items():
            meta = {"id": sid, **SOURCES[sid]}
            try:
                data[sid] = fut.result()
                meta["status"] = "ok"
            except Exception as e:  # noqa: BLE001 — a source being down shouldn't sink the others
                log.warning("Retrograde source %s failed: %s", sid, e)
                meta.update(status="error", error=str(e)[:200])
            sources.append(meta)
    if not data:
        raise RuntimeError("No ephemeris source could be reached")

    reference = next(sid for sid in _FETCHERS if sid in data)
    lo_day, hi_day = (lo - start).days, (hi - start).days + 1
    periods = []
    for pid, name, *_ in PLANETS:
        stations = {sid: find_stations(series[pid]) for sid, series in data.items()}
        for p in _periods(data[reference][pid]):
            if p["d"]["day"] < lo_day or p["r"]["day"] >= hi_day:
                continue
            checks = {}
            for key in ("r", "d"):
                ref = p[key]
                times = {}
                for sid, found in stations.items():
                    m = _match(ref["day"], ref["kind"], found)
                    times[sid] = m["day"] if m else None
                got = [t for t in times.values() if t is not None]
                spread = (max(got) - min(got)) * 24 if len(got) > 1 else 0.0
                checks[key] = {
                    # The consensus time is the median, so one stray source can't drag it.
                    "time": _iso(start, statistics.median(got)),
                    "by_source": {sid: _iso(start, t) for sid, t in times.items()},
                    "spread_hours": round(spread, 2),
                    "agree": sum(1 for t in got if abs(t - statistics.median(got)) * 24 <= AGREE_HOURS),
                }
            n = len(data)
            agree = min(checks["r"]["agree"], checks["d"]["agree"])
            status = "verified" if agree == n and n >= 2 else "single" if n == 1 else "conflict" if agree < 2 else "partial"
            periods.append({
                "planet": pid, "name": name,
                "start": checks["r"]["time"], "end": checks["d"]["time"],
                "shadow_start": _iso(start, p["shadow_start"]), "shadow_end": _iso(start, p["shadow_end"]),
                "station_retrograde": {**_sign(p["r"]["lon"]), **checks["r"]},
                "station_direct": {**_sign(p["d"]["lon"]), **checks["d"]},
                "verification": {"status": status, "sources_agreeing": agree, "sources_available": n,
                                 "max_spread_hours": max(checks["r"]["spread_hours"], checks["d"]["spread_hours"])},
            })
    periods.sort(key=lambda p: p["start"])
    for s in sources:
        if s["id"] in data:
            s["stations"] = sum(len(find_stations(series)) for series in data[s["id"]].values())

    return {
        "range": {"start": lo.isoformat(), "end": hi.isoformat()},
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "reference": reference,
        "agree_hours": AGREE_HOURS,
        "planets": [{"id": pid, "name": name} for pid, name, *_ in PLANETS],
        "sources": sources,
        "periods": periods,
    }


def calendar(start_year: int, end_year: int, refresh: bool = False) -> dict:
    path = data_path(f"retrograde_{start_year}_{end_year}.json")
    cached = load_json(path, None)
    if cached and not refresh:
        complete = all(s["status"] == "ok" for s in cached["result"]["sources"])
        if time.time() - cached["saved"] < (CACHE_OK if complete else CACHE_PARTIAL):
            return cached["result"]
    result = build(start_year, end_year)
    save_json(path, {"saved": time.time(), "result": result})
    return result
