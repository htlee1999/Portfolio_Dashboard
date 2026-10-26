"""Do sector ETFs behave differently while planets are retrograde?

An event study. Each trading day is marked inside or outside the chosen retrograde (or shadow)
windows, and an ETF's daily returns on inside days are compared with outside days, both
absolute and in excess of the S&P 500 (SPY).

Significance comes from a circular-shift test rather than a t-test. The whole retrograde
calendar is slid along the return history by every possible offset, keeping the real
lengths and spacing of the periods, and the observed gap is compared with all the
shifted ones. That respects volatility clustering (calm and stormy markets come in runs),
which makes a plain t-test far too eager. Every shift is computed at once with an FFT.

Many ETFs times many planets means many tests, so p-values also get a Benjamini–Hochberg
q-value: the false-discovery-adjusted figure to judge "significant" by.
"""

import logging
import math
from datetime import date, datetime, timezone

import numpy as np
import pandas as pd
import yfinance as yf

from . import market, retrograde
from .utils import ttl_cache

log = logging.getLogger(__name__)

BENCHMARK = "SPY"
# (symbol, name, group)
ETFS = [
    ("SPY", "S&P 500", "Benchmark"),
    ("QQQ", "Nasdaq 100", "Broad market"),
    ("SMH", "Semiconductors (VanEck)", "Semiconductors"),
    ("SOXX", "Semiconductors (iShares)", "Semiconductors"),
    ("DTCR", "Data Center & Digital Infrastructure (Global X)", "Data centres"),
    ("SRVR", "Data & Infrastructure Real Estate (Pacer)", "Data centres"),
    ("VNQ", "US REITs (Vanguard)", "REITs"),
    ("XLRE", "Real Estate Select Sector", "REITs"),
    ("XLK", "Technology", "Sectors"),
    ("XLC", "Communication Services", "Sectors"),
    ("XLY", "Consumer Discretionary", "Sectors"),
    ("XLP", "Consumer Staples", "Sectors"),
    ("XLE", "Energy", "Sectors"),
    ("XLF", "Financials", "Sectors"),
    ("XLV", "Health Care", "Sectors"),
    ("XLI", "Industrials", "Sectors"),
    ("XLB", "Materials", "Sectors"),
    ("XLU", "Utilities", "Sectors"),
    ("GLD", "Gold", "Other"),
]
KNOWN = {s: (name, group) for s, name, group in ETFS}

TRADING_DAYS = 252
MIN_DAYS = 20               # fewer inside (or outside) days than this: too few to test
EXCLUDE_SHIFT = 63          # ignore shifts within ~3 months, which mostly overlap the real calendar
CHUNK_YEARS = retrograde.MAX_SPAN
MARKET_CLOSE_UTC = 21       # a trading day counts as "inside" if the window covers its close


# ── Inputs ───────────────────────────────────────────────────────────────────

def all_periods(start_year: int, end_year: int) -> list[dict]:
    """Retrograde periods across any span, assembled from the cached five-year calendars."""
    seen, out = set(), []
    for y in range(start_year, end_year + 1, CHUNK_YEARS):
        chunk = retrograde.calendar(y, min(y + CHUNK_YEARS - 1, end_year))
        for p in chunk["periods"]:
            key = (p["planet"], p["start"][:10])
            if key not in seen:
                seen.add(key)
                out.append(p)
    return sorted(out, key=lambda p: p["start"])


@ttl_cache(3600)
def closes(symbols: tuple[str, ...], since: str) -> pd.DataFrame | None:
    if not market.yahoo_available():
        return None
    try:
        data = yf.download(list(symbols), start=since, auto_adjust=True, progress=False, threads=True)
    except Exception:  # noqa: BLE001
        log.warning("Price download failed", exc_info=True)
        return None
    if data is None or data.empty:
        return None
    frame = data["Close"] if isinstance(data.columns, pd.MultiIndex) else data[["Close"]].rename(columns={"Close": symbols[0]})
    return frame.dropna(how="all")


# ── Statistics ───────────────────────────────────────────────────────────────

def _ts(iso: str | None) -> pd.Timestamp | None:
    return pd.Timestamp(iso).tz_convert("UTC") if iso else None


def indicator(index: pd.DatetimeIndex, windows: list[tuple[pd.Timestamp, pd.Timestamp]]) -> np.ndarray:
    """1 for trading days whose close falls inside any window."""
    close = pd.DatetimeIndex(index).tz_localize("UTC") + pd.Timedelta(hours=MARKET_CLOSE_UTC)
    out = np.zeros(len(index), dtype=bool)
    for a, b in windows:
        out |= (close >= a) & (close < b)
    return out


def shift_test(x: np.ndarray, y: np.ndarray) -> tuple[float, float, int]:
    """Observed inside-minus-outside mean, its two-sided circular-shift p-value, and shifts used."""
    n = len(y)
    n_in = int(x.sum())
    total = y.sum()
    # c[k] = sum of y over the inside days after sliding the calendar k days, for every k at once.
    c = np.fft.irfft(np.conj(np.fft.rfft(x.astype(float))) * np.fft.rfft(y), n)
    stat = c / n_in - (total - c) / (n - n_in)
    observed = stat[0]
    k = np.arange(n)
    usable = np.minimum(k, n - k) >= EXCLUDE_SHIFT
    null = stat[usable]
    p = (1 + np.sum(np.abs(null) >= abs(observed) - 1e-15)) / (1 + len(null))
    return float(observed), float(p), int(len(null))


def bh_qvalues(pvalues: list[float]) -> list[float]:
    """Benjamini–Hochberg adjusted p-values (q-values), in the input order."""
    m = len(pvalues)
    if not m:
        return []
    order = np.argsort(pvalues)
    ranked = np.array(pvalues)[order] * m / np.arange(1, m + 1)
    ranked = np.minimum.accumulate(ranked[::-1])[::-1].clip(max=1.0)
    out = np.empty(m)
    out[order] = ranked
    return out.tolist()


def _ann(mean_log: float) -> float:
    """Mean daily log return → annualized simple return, in %."""
    return round(math.expm1(mean_log * TRADING_DAYS) * 100, 2)


def compare(y: np.ndarray, x: np.ndarray) -> dict | None:
    n_in, n_out = int(x.sum()), int((~x).sum())
    if n_in < MIN_DAYS or n_out < MIN_DAYS:
        return None
    diff, p, shifts = shift_test(x, y)
    yi, yo = y[x], y[~x]
    return {
        "days_in": n_in, "days_out": n_out,
        "ann_in": _ann(yi.mean()), "ann_out": _ann(yo.mean()),
        "diff": round(_ann(yi.mean()) - _ann(yo.mean()), 2),
        "daily_diff_bp": round(diff * 1e4, 2),
        "vol_in": round(yi.std(ddof=1) * math.sqrt(TRADING_DAYS) * 100, 2),
        "vol_out": round(yo.std(ddof=1) * math.sqrt(TRADING_DAYS) * 100, 2),
        "up_in": round(float((yi > 0).mean()) * 100, 1), "up_out": round(float((yo > 0).mean()) * 100, 1),
        "p": round(p, 4), "shifts": shifts,
    }


# ── Analysis ─────────────────────────────────────────────────────────────────

def analyze(symbols: list[str], planets: list[str], since: int, window: str) -> dict:
    today = date.today()
    symbols = list(dict.fromkeys([BENCHMARK, *symbols]))
    periods = [p for p in all_periods(since, today.year) if p["planet"] in planets]
    prices = closes(tuple(symbols), f"{since}-01-01")
    if prices is None:
        raise RuntimeError("Could not download prices from Yahoo Finance — it may be rate-limiting; try again shortly.")
    missing = [s for s in symbols if s not in prices.columns or prices[s].dropna().empty]
    if BENCHMARK in missing:
        raise RuntimeError("Could not download S&P 500 (SPY) prices")
    symbols = [s for s in symbols if s not in missing]

    names = {pid: name for pid, name, *_ in retrograde.PLANETS}
    shadow = window == "shadow"

    def span(p: dict) -> tuple[pd.Timestamp, pd.Timestamp]:
        a = _ts(p["shadow_start"] if shadow and p["shadow_start"] else p["start"])
        b = _ts(p["shadow_end"] if shadow and p["shadow_end"] else p["end"])
        return a, b

    # Tests: each planet alone, plus "any" and "overlap (2+)" when more than one is chosen.
    tests = [{"id": pid, "label": names[pid], "planets": [pid]} for pid in planets]
    if len(planets) > 1:
        tests += [{"id": "any", "label": "Any selected", "planets": planets},
                  {"id": "overlap", "label": "Overlap (2+)", "planets": planets}]

    log_ret = np.log(prices[symbols]).diff()
    bench = log_ret[BENCHMARK]
    results, pvals = [], []
    for sym in symbols:
        r = log_ret[sym].dropna()
        r = r[r.index > r.index[0]]  # first day has no prior close
        excess = (r - bench.reindex(r.index)).dropna()
        row = {"symbol": sym, "name": KNOWN.get(sym, (sym, "Custom"))[0], "group": KNOWN.get(sym, (sym, "Custom"))[1],
               "first_date": r.index[0].date().isoformat(), "days": len(r), "tests": {}}
        for t in tests:
            spans = {pid: [span(p) for p in periods if p["planet"] == pid] for pid in t["planets"]}
            if t["id"] == "overlap":
                x = sum(indicator(r.index, s).astype(int) for s in spans.values()) >= 2
                xe = sum(indicator(excess.index, s).astype(int) for s in spans.values()) >= 2
            else:
                flat = [w for s in spans.values() for w in s]
                x, xe = indicator(r.index, flat), indicator(excess.index, flat)
            entry = {"absolute": compare(r.to_numpy(), x)}
            if sym != BENCHMARK:
                entry["excess"] = compare(excess.to_numpy(), xe)
            for kind, res in entry.items():
                if res:
                    pvals.append((sym, t["id"], kind, res["p"]))
            row["tests"][t["id"]] = entry
        results.append(row)

    qs = bh_qvalues([p for *_, p in pvals])
    for (sym, tid, kind, _), q in zip(pvals, qs):
        res = next(r for r in results if r["symbol"] == sym)["tests"][tid][kind]
        res["q"] = round(q, 4)

    # Each period's own return for every ETF, against SPY and against a typical window of
    # the same length (the average of every same-length stretch in that ETF's history).
    closes_ = prices[symbols]
    cum = log_ret[symbols].fillna(0).cumsum()
    by_period = []
    for p in periods:
        a, b = span(p)
        idx = closes_.index.tz_localize("UTC") + pd.Timedelta(hours=MARKET_CLOSE_UTC)
        inside = np.where((idx >= a) & (idx < b))[0]
        if len(inside) < 2:
            continue
        i0, i1 = max(inside[0] - 1, 0), inside[-1]
        length = i1 - i0
        row = {"planet": p["planet"], "start": a.isoformat(), "end": b.isoformat(),
               "trading_days": int(length), "complete": bool(b.date() <= today), "returns": {}}
        for sym in symbols:
            s = closes_[sym]
            if pd.isna(s.iloc[i0]) or pd.isna(s.iloc[i1]):
                continue
            windows = cum[sym][s.first_valid_index():].diff(length).dropna()
            row["returns"][sym] = {
                "ret": round((s.iloc[i1] / s.iloc[i0] - 1) * 100, 2),
                "typical": round(math.expm1(windows.mean()) * 100, 2) if len(windows) else None,
                # How often any stretch of this length lost money: the base rate for "it fell".
                "typical_down": round(float((windows < 0).mean()) * 100, 1) if len(windows) else None,
            }
        by_period.append(row)

    weekly = closes_.resample("W-FRI").last()
    growth = (weekly / weekly.apply(lambda c: c.dropna().iloc[0] if c.notna().any() else np.nan)).round(4)

    retro_days = {t["id"]: None for t in tests}
    for t in tests:
        res = results[0]["tests"][t["id"]]["absolute"]
        retro_days[t["id"]] = round(res["days_in"] / (res["days_in"] + res["days_out"]) * 100, 1) if res else None

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "since": since, "window": window, "benchmark": BENCHMARK,
        "planets": planets, "missing": missing,
        "tests": [{**t, "share_of_days": retro_days[t["id"]]} for t in tests],
        "results": results,
        "periods": by_period,
        "growth": [{"date": d.date().isoformat(), **{k: (None if pd.isna(v) else float(v)) for k, v in row.items()}}
                   for d, row in growth.iterrows()],
        "method": {"min_days": MIN_DAYS, "exclude_shift_days": EXCLUDE_SHIFT, "tests_run": len(pvals)},
    }


@ttl_cache(3600)
def cached_analysis(symbols: tuple[str, ...], planets: tuple[str, ...], since: int, window: str) -> dict:
    return analyze(list(symbols), list(planets), since, window)
