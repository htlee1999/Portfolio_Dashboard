"""Does the evaluation catch errors? A planted-error benchmark against the live Gemini review.

Each case plants one known error in a saved real one-shot (tests/fixtures) and runs the full
review. It counts as caught when a skill expected to own that error raises a minor or major
challenge. Some errors are ones a rule screen matches; others no screen covers, so only the
model can catch them. The unaltered one-shots measure false alarms.

Run with: PYTHONPATH=. python -m backend.evaluation_benchmark [--runs 3] [--verbose] [--json out.json]
Every review is a real Gemini call (about 6,000 tokens each), logged as assessment_evaluation.
The five-year back-test fetches live prices.
"""

import argparse
import copy
import json
import re
import threading
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Callable

from . import evaluation

FIXTURES = Path(__file__).parent.parent / "tests" / "fixtures"


def _load(name: str) -> tuple[dict, dict]:
    data = json.loads((FIXTURES / f"assessment_{name}.json").read_text())
    return data["context"], data["ai"]


def _plant(sentence: str) -> Callable:
    def edit(ctx: dict, ai: dict) -> tuple[dict, dict]:
        ai = copy.deepcopy(ai)
        ai["steps"][0]["content"] += " " + sentence
        return ctx, ai
    return edit


def _replace(old: str, new: str) -> Callable:
    def edit(ctx: dict, ai: dict) -> tuple[dict, dict]:
        ai = copy.deepcopy(ai)
        hits = [s for s in ai["steps"] if old in s["content"]]
        assert hits, f"{old!r} isn't in the fixture"
        for s in hits:
            s["content"] = s["content"].replace(old, new)
        return ctx, ai
    return edit


def _rsi_word(ctx: dict, ai: dict) -> tuple[dict, dict]:
    word = "oversold" if ctx["technical"]["signals"]["rsi"]["value"] > 35 else "overbought"
    return _plant(f"RSI shows the stock is {word}.")(ctx, ai)


def _target_above_analysts(ctx: dict, ai: dict) -> tuple[dict, dict]:
    return ctx, {**ai, "price_target": round(ctx["fundamental"]["analyst"]["target_high"] * 1.2, 2)}


def _buy_dismissing_valuation(ctx: dict, ai: dict) -> tuple[dict, dict]:
    """AAPL as a BUY whose only answer to a valuation score of 20 is "despite"."""
    ai = copy.deepcopy(ai)
    ai["recommendation"] = "BUY"
    ai["summary"] = "Apple combines strong profitability, consistent earnings beats and an intact uptrend, which outweigh its valuation."
    ai["position_advice"] = "Build a position now; quality like this rarely gets cheap."
    ai["steps"][1]["content"] = ("The company demonstrates solid financial health with a strong Piotroski F-score of 8/9, consistent "
                                 "earnings beats and expanding margins. Despite a stretched valuation, quality deserves a premium.")
    ai["risks"] = [r for r in ai["risks"] if not any(w in r.lower() for w in ("valuation", "p/e", "multiple", "premium"))]
    return ctx, ai


def _anchored_position(ctx: dict, ai: dict) -> tuple[dict, dict]:
    price = ctx["technical"]["quote"]["price"]
    ctx = {**ctx, "position": {"lots": 1, "quantity": 20, "avg_cost": round(price * 1.18, 2), "invested": price * 1.18 * 20,
                               "value": price * 20, "unrealized": -price * 0.18 * 20, "unrealized_pct": -15.3, "currency": "USD"}}
    return ctx, {**ai, "position_advice": "Hold until the shares climb back to the price you paid, then sell."}


# (name, fixture, edit, skills expected to run, marker). A case counts as caught only when a challenge
# names the planted error (the marker matches its text), not merely when the right skill objects to
# something: the unaltered one-shots draw challenges of their own. None marks an unaltered one-shot.
Case = tuple[str, str, Callable | None, tuple[str, ...], str]
CLEAN_CASES: list[Case] = [("clean", "aapl", None, (), ""), ("clean", "rivn", None, (), "")]
# Errors a rule screen matches.
SCREENED_CASES: list[Case] = [
    ("RSI called oversold/overbought", "aapl", _rsi_word, ("claim-check",), r"oversold|overbought"),
    ("RSI called oversold/overbought", "rivn", _rsi_word, ("claim-check",), r"oversold|overbought"),
    ("Forecast without skill relied on", "aapl", _plant("The gradient boosting model predicts a further rise next session."),
     ("claim-check",), r"gradient|forecast|model"),
    ("Forecast without skill relied on", "rivn", _plant("The gradient boosting model predicts a further rise next session."),
     ("claim-check",), r"gradient|forecast|model"),
    ("Wrong side of the 200-day", "rivn", _plant("The price is above the 200-day average."), ("claim-check",), r"200"),
    ("Target 20% above every analyst's", "aapl", _target_above_analysts, ("valuation-sanity",),
     r"486|405|analysts'? high|above (every|all|the highest) analyst"),
    ("BUY dismisses valuation without figures", "aapl", _buy_dismissing_valuation, ("counter-case", "valuation-sanity"),
     r"dismiss|without (sufficient )?(quantitative |numerical )?(figures|evidence|numbers|justification)|against the call|opposing signal"),
]
# Errors no screen covers: only the model can catch these.
UNSCREENED_CASES: list[Case] = [
    ("Wrong P/E figure", "aapl", _replace("P/E of 39.04", "P/E of 19.52"), ("claim-check",), r"19\.5"),
    ("Wrong RSI figure", "rivn", _replace("RSI of 37.76", "RSI of 57.76"), ("claim-check",), r"57\.7"),
    ("Wrong distance from 52-week high", "aapl", _plant("The stock sits about 30% below its 52-week high."), ("claim-check",),
     r"30 ?%|30 percent"),
    ("Wrong analyst consensus", "aapl", _plant("Analysts' consensus rating on the stock is sell."), ("claim-check",), r"\bsell\b"),
    ("Earnings date misstated", "aapl", _plant("No earnings report is due before next year."), ("claim-check", "earnings-window"),
     r"next year|no earnings report is due"),
    ("Advice anchored on purchase price", "aapl", _anchored_position, ("position-review",), r"cost|paid|purchase|anchor"),
]
CASES = CLEAN_CASES + SCREENED_CASES + UNSCREENED_CASES


def _challenges(out: dict, skills: tuple[str, ...] | None = None) -> list[dict]:
    return [f for f in out["findings"] if f["stance"] == "challenges" and f["severity"] != "info"
            and (skills is None or f["skill"] in skills)]


class _Pace:
    """Spaces Gemini calls to stay under a requests-per-minute quota (the free tier allows 15)."""

    def __init__(self, rpm: int):
        self.gap, self.next, self.lock = 60 / rpm, 0.0, threading.Lock()

    def wait(self) -> None:
        with self.lock:
            now = time.monotonic()
            start = max(now, self.next)
            self.next = start + self.gap
        time.sleep(start - now)


_pace = _Pace(12)


def _review(ctx: dict, ai: dict, attempts: int = 3) -> dict:
    for attempt in range(attempts):
        _pace.wait()
        try:
            return evaluation.review("benchmark", ctx, ai)
        except RuntimeError as e:
            if "429" not in str(e) or attempt == attempts - 1:
                raise
            time.sleep(60)  # the quota window is a minute
    raise AssertionError("unreachable")


def _caught(challenges: list[str], marker: str) -> bool:
    return any(re.search(marker, c, re.IGNORECASE) for c in challenges)


def _run(case: tuple, run: int) -> dict:
    name, fixture, edit, expected, marker = case
    ctx, ai = _load(fixture)
    if edit:
        ctx, ai = edit(ctx, ai)
    chosen = evaluation.select("benchmark", ctx, ai)
    missing = [s for s in expected if s not in {c["name"] for c in chosen}]
    try:
        out = _review(ctx, ai)
    except RuntimeError as e:
        return {"case": name, "fixture": fixture, "run": run, "expected": expected, "error": str(e)[:200]}
    return {
        "case": name, "fixture": fixture, "run": run, "expected": expected, "skills_missing": missing,
        # Whether a screen in an expected skill failed: these errors don't depend on the model alone.
        "screened": any(not c["passed"] for c in out["checks"] if c["skill"] in expected),
        "marker": marker,
        "caught": _caught([f["finding"] for f in _challenges(out)], marker) if marker else None,
        "verdict": out["verdict"], "confidence": [ai["confidence"], out["confidence_adjusted"]],
        "challenges": [f"[{f['skill']}, {f['severity']}] {f['finding']}" for f in _challenges(out)],
    }


def _summary(results: list[dict], verbose: bool) -> str:
    lines, groups = [], {}
    failed = [r for r in results if "error" in r]
    results = [r for r in results if "error" not in r]
    for r in results:
        groups.setdefault((r["case"], r["fixture"]), []).append(r)
    width = max((len(f"{c} ({f})") for c, f in groups), default=4)
    clean_runs = {f: [r for r in results if r["caught"] is None and r["fixture"] == f] for f in {r["fixture"] for r in results}}
    lines.append(f"{'Case':<{width}}  {'Screen':<6}  {'Caught':<6}  {'Control':<7}  Verdicts")
    for (case, fixture), runs in groups.items():
        verdicts = Counter(r["verdict"] for r in runs)
        caught = "—" if runs[0]["caught"] is None else f"{sum(r['caught'] for r in runs)}/{len(runs)}"
        screen = "—" if not runs[0]["expected"] else "yes" if all(r["screened"] for r in runs) else "no"
        # The same marker on the unaltered one-shot's challenges: should be 0, or the marker is too loose.
        control = "—" if runs[0]["caught"] is None else (
            f"{sum(_caught(r['challenges'], runs[0]['marker']) for r in clean_runs.get(fixture, []))}/{len(clean_runs.get(fixture, []))}")
        lines.append(f"{f'{case} ({fixture})':<{width}}  {screen:<6}  {caught:<6}  {control:<7}  "
                     + ", ".join(f"{v} ×{n}" for v, n in verdicts.most_common()))
        for r in runs:
            if r["skills_missing"]:
                lines.append(f"    run {r['run']}: expected skill not selected: {', '.join(r['skills_missing'])}")
            if verbose or (r["caught"] is None and r["challenges"]):
                lines += [f"    run {r['run']}: {c}" for c in r["challenges"]]

    def rate(rows: list[dict]) -> str:
        return f"{sum(r['caught'] for r in rows)}/{len(rows)}" if rows else "0/0"

    planted = [r for r in results if r["caught"] is not None]
    clean = [r for r in results if r["caught"] is None]
    lines += [
        "",
        f"Caught, errors a screen matched:  {rate([r for r in planted if r['screened']])}",
        f"Caught, errors no screen matched: {rate([r for r in planted if not r['screened']])}",
        f"Unaltered runs with any challenge: {sum(bool(r['challenges']) for r in clean)}/{len(clean)} "
        "(read them: some may be real weaknesses in the original)",
        f"Cases with the same verdict on every run: "
        f"{sum(len({r['verdict'] for r in runs}) == 1 for runs in groups.values())}/{len(groups)}",
    ]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--runs", type=int, default=1, help="reviews per case, to see how stable the verdict is")
    parser.add_argument("--verbose", action="store_true", help="print every challenge")
    parser.add_argument("--json", type=Path, help="also write the raw results here")
    parser.add_argument("--rpm", type=int, default=12, help="Gemini requests per minute (free tier: 15)")
    parser.add_argument("--rescore", type=Path, help="re-score results saved with --json, without calling Gemini")
    args = parser.parse_args()
    if args.rescore:
        markers = {(c[0], c[1]): c[4] for c in CASES}
        results = json.loads(args.rescore.read_text())
        for r in results:
            marker = markers[(r["case"], r["fixture"])]
            r["marker"] = marker
            r["caught"] = _caught([c.split("] ", 1)[-1] for c in r.get("challenges", [])], marker) if marker else None
        print(_summary(results, args.verbose))
        return
    global _pace
    _pace = _Pace(args.rpm)

    # Benchmark positions are planted in the context; don't look up a real portfolio.
    evaluation._portfolio_extra = lambda username, ctx: {}
    jobs = [(case, run) for case in CASES for run in range(1, args.runs + 1)]
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda job: _run(*job), jobs))
    print(_summary(results, args.verbose))
    if args.json:
        args.json.write_text(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
