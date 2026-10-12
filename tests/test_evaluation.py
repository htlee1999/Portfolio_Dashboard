"""Skill selection, rule screens and rule enforcement for the assessment evaluation.

Fixtures are real assessment contexts and one-shot results (AAPL and RIVN, October 2026).
Nothing here calls Gemini or the network: the five-year back-test is stubbed.

Run with: PYTHONPATH=. pytest tests
"""

import copy
import json
from datetime import timedelta, timezone
from pathlib import Path

import pandas as pd
import pytest

from backend import evaluation

FIXTURES = Path(__file__).parent / "fixtures"


def _load(name: str) -> tuple[dict, dict]:
    data = json.loads((FIXTURES / f"assessment_{name}.json").read_text())
    return data["context"], data["ai"]


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    # A MACD sell signal that fired recently and has no edge on this stock.
    backtest = {"start": "2021-10-08", "end": "2026-10-08", "signals": [
        {"id": "macd_bear", "indicator": "macd", "label": "MACD crosses below signal", "expect": "down", "count": 41,
         "last": "2026-09-29", "horizons": [{"days": 20, "hit_rate": 0.38, "baseline_hit": 0.40, "verdict": "no_edge"}]},
        {"id": "rsi_overbought", "indicator": "rsi", "label": "RSI rises above 70", "expect": "down", "count": 9,
         "last": "2026-07-01", "horizons": [{"days": 20, "hit_rate": 0.5, "baseline_hit": 0.4, "verdict": "insufficient"}]},
    ]}
    monkeypatch.setattr(evaluation.technical, "backtest", lambda *a, **k: backtest)
    monkeypatch.setattr(evaluation, "_portfolio_extra", lambda username, ctx: {})


def _checks(ctx: dict, ai: dict) -> dict[str, list[dict]]:
    return {c["name"]: c["checks"] for c in evaluation.select("test", ctx, ai)}


def _failed(ctx: dict, ai: dict, skill: str) -> list[str]:
    return [c["check"] for c in _checks(ctx, ai).get(skill, []) if not c["passed"]]


def _plant(ai: dict, sentence: str) -> dict:
    ai = copy.deepcopy(ai)
    ai["steps"][0]["content"] += " " + sentence
    return ai


# ── Skill files ──────────────────────────────────────────────────────────────

def test_every_skill_has_a_facts_function_and_complete_metadata():
    skills = evaluation.skills()
    assert set(skills) == set(evaluation.FACTS)
    for s in skills.values():
        assert s["title"] and s["description"] and s["applies_when"] and s["rationale"] and s["body"]
        assert s["evidence"] in ("strong", "mixed", "weak")
        assert s["sources"] and all(x["url"].startswith("https://") for x in s["sources"])


# ── Selection ────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("name", ["aapl", "rivn"])
def test_claims_and_counter_case_always_run(name):
    ctx, ai = _load(name)
    assert {"claim-check", "counter-case"} <= set(_checks(ctx, ai))


def test_hold_without_target_skips_valuation_and_entry_plan():
    ctx, ai = _load("aapl")
    ai = {**ai, "recommendation": "HOLD", "price_target": None, "position_advice": "Hold off for now."}
    chosen = set(_checks(ctx, ai))
    assert "valuation-sanity" not in chosen and "entry-plan" not in chosen


def test_buy_gets_an_entry_plan_and_sell_does_not():
    ctx, ai = _load("aapl")
    assert "entry-plan" in _checks(ctx, {**ai, "recommendation": "BUY"})
    assert "entry-plan" not in _checks(ctx, {**ai, "recommendation": "SELL", "position_advice": "Do not add."})


def test_position_review_only_when_held():
    ctx, ai = _load("aapl")
    assert "position-review" not in _checks(ctx, ai)
    held = {**ctx, "position": {"lots": 1, "quantity": 10, "avg_cost": 200.0, "invested": 2000.0, "value": 3400.0,
                                "unrealized": 1400.0, "unrealized_pct": 70.0, "currency": "USD"}}
    assert "position-review" in _checks(held, ai)


def test_earnings_window_needs_the_report_inside_the_horizon():
    ctx, ai = _load("aapl")
    assert "earnings-window" in _checks(ctx, ai)
    later = copy.deepcopy(ctx)
    later["fundamental"]["earnings"]["next_date"] = "2027-06-01"
    assert "earnings-window" not in _checks(later, {**ai, "time_horizon": "Short-term"})


# ── Rule screens: the real one-shots pass, planted errors are caught ─────────

@pytest.mark.parametrize("name", ["aapl", "rivn"])
def test_real_one_shot_passes_claim_check(name):
    ctx, ai = _load(name)
    assert _failed(ctx, ai, "claim-check") == []


@pytest.mark.parametrize("name", ["aapl", "rivn"])
def test_planted_rsi_misreading(name):
    ctx, ai = _load(name)
    rsi = ctx["technical"]["signals"]["rsi"]["value"]
    word = "oversold" if rsi > 35 else "overbought"
    assert "RSI reading" in _failed(ctx, _plant(ai, f"RSI shows the stock is {word}."), "claim-check")


def test_hedged_rsi_wording_is_not_flagged():
    ctx, ai = _load("aapl")  # RSI about 61
    assert _failed(ctx, _plant(ai, "RSI is approaching overbought but is not overbought yet."), "claim-check") == []


@pytest.mark.parametrize("name", ["aapl", "rivn"])
def test_planted_forecast_reliance(name):
    ctx, ai = _load(name)
    assert not ctx["predictive"]["any_skill"]
    planted = _plant(ai, "The gradient boosting model predicts a further rise next session.")
    assert "Forecast reliance" in _failed(ctx, planted, "claim-check")


def test_saying_models_have_no_edge_is_not_reliance():
    ctx, ai = _load("aapl")
    ok = _plant(ai, "Gradient boosting models suggest no significant edge over a no-change forecast.")
    assert "Forecast reliance" not in _failed(ctx, ok, "claim-check")


def test_planted_200_day_misreading():
    ctx, ai = _load("rivn")  # trades below its 200-day average
    assert "200-day average" in _failed(ctx, _plant(ai, "The price is above the 200-day average."), "claim-check")


def test_sentiment_discussed_when_not_included():
    ctx, ai = _load("aapl")
    assert ctx["sentiment"] is None
    assert "Missing data" in _failed(ctx, _plant(ai, "Positive news sentiment supports the case."), "claim-check")


def test_target_above_every_analyst_is_flagged():
    ctx, ai = _load("aapl")
    high = ctx["fundamental"]["analyst"]["target_high"]
    assert "Target vs analysts" in _failed(ctx, {**ai, "price_target": high * 1.15}, "valuation-sanity")
    assert "Target vs analysts" not in _failed(ctx, {**ai, "price_target": high * 0.9}, "valuation-sanity")


def test_unmentioned_earnings_report_is_flagged():
    ctx, ai = _load("aapl")  # next report 24 days after the context date
    silent = copy.deepcopy(ai)
    for key in ("summary", "position_advice"):
        silent[key] = "Hold."
    silent["strengths"], silent["risks"] = ["Strong margins"], ["Valuation"]
    silent["steps"] = [{"title": "Technical picture", "content": "The trend is up."}]
    assert "Report acknowledged" in _failed(ctx, silent, "earnings-window")


def test_past_earnings_beats_dont_count_as_acknowledging_the_next_report():
    ctx, ai = _load("aapl")  # mentions "consistent recent earnings beats", never the 2 November report
    assert "Report acknowledged" in _failed(ctx, ai, "earnings-window")
    for sentence in ("The upcoming earnings report adds event risk.", "Results are due on 2 November.", "Earnings in 24 days could move the stock."):
        assert "Report acknowledged" not in _failed(ctx, _plant(ai, sentence), "earnings-window"), sentence


def test_only_current_recent_technical_signals_are_screened():
    ctx, ai = _load("aapl")  # MACD bearish now; the RSI sell signal fired months ago
    failed = _failed(ctx, ai, "technical-evidence")
    assert failed == ["MACD crosses below signal"]


def _as_buy(ai: dict, valuation_sentence: str) -> dict:
    """AAPL (valuation score 20) as a BUY whose only valuation wording is ``valuation_sentence``."""
    ai = copy.deepcopy(ai)
    ai["recommendation"], ai["summary"], ai["position_advice"] = "BUY", "Strong quality.", "Buy."
    ai["risks"] = ["Supply chain"]
    ai["steps"] = [{"title": "Fundamentals", "content": valuation_sentence}]
    return ai


def test_counter_case_needs_figures_to_count_an_opposing_axis_as_answered():
    ctx, ai = _load("aapl")
    detail = lambda ai: next(c for c in _checks(ctx, ai)["counter-case"] if c["check"] == "Valuation addressed")
    absent = detail(_as_buy(ai, "Margins keep expanding."))
    dismissed = detail(_as_buy(ai, "Despite a stretched valuation, quality deserves a premium."))
    answered = detail(_as_buy(ai, "At a P/E of 39 the valuation is rich, but EPS growth of 12% supports it."))
    assert not absent["passed"] and "isn't discussed" in absent["detail"]
    assert not dismissed["passed"] and "without figures" in dismissed["detail"]
    assert answered["passed"]


def test_every_skill_says_what_its_screens_cover():
    assert set(evaluation.SCREENED) == set(evaluation.FACTS)
    prompt = evaluation._prompt(*_load("aapl"), evaluation.select("test", *_load("aapl")))
    assert prompt.count("Automatic screens cover only:") == len(evaluation.select("test", *_load("aapl")))


def test_anchoring_and_concentration(monkeypatch):
    ctx, ai = _load("aapl")
    held = {**ctx, "position": {"lots": 2, "quantity": 10, "avg_cost": 400.0, "invested": 4000.0, "value": 3400.0,
                                "unrealized": -600.0, "unrealized_pct": -15.0, "currency": "USD"}}
    monkeypatch.setattr(evaluation, "_portfolio_extra", lambda username, ctx: {"weight_pct": 35.0, "holdings": 4, "largest_other_pct": 30.0})
    ai = {**ai, "recommendation": "BUY", "position_advice": "Add to the position to lower your average cost."}
    failed = _failed(held, ai, "position-review")
    assert "Anchoring" in failed and "Concentration" in failed


# ── Enforcement of the evaluation's rules ────────────────────────────────────

def _out(**kw) -> dict:
    base = {"verdict": "stands", "confidence_adjusted": 9, "summary": "", "counter_case": "", "invalidation": [],
            "entry_plan": {"approach": "staged", "detail": "", "size": "", "review_when": ""},
            "findings": [{"skill": "claim-check", "stance": "challenges", "severity": "major", "finding": "x"},
                         {"skill": "made-up", "stance": "supports", "severity": "info", "finding": "y"}]}
    return {**base, **kw}


def test_enforce_caps_confidence_and_drops_unknown_skills():
    out = evaluation.enforce(_out(), {"confidence": 6}, ["claim-check", "counter-case"])
    assert out["confidence_adjusted"] == 6
    assert [f["skill"] for f in out["findings"]] == ["claim-check"]


def test_enforce_downgrades_stands_with_a_major_challenge_and_drops_unrequested_plan():
    out = evaluation.enforce(_out(), {"confidence": 6}, ["claim-check", "counter-case"])
    assert out["verdict"] == "weakened"
    assert out["entry_plan"] is None
    kept = evaluation.enforce(_out(), {"confidence": 6}, ["claim-check", "entry-plan"])
    assert kept["entry_plan"] is not None


# ── Saving to history ────────────────────────────────────────────────────────

def test_update_history_attaches_to_the_matching_record(tmp_path, monkeypatch):
    from backend import storage
    monkeypatch.setattr(storage, "history_path", lambda username: str(tmp_path / f"h_{username}.json"))
    storage.append_history("u", {"symbol": "AAPL", "timestamp": "2026-10-09T10:00:00", "recommendation": "HOLD"})
    storage.append_history("u", {"symbol": "AAPL", "timestamp": "2026-10-09T11:00:00", "recommendation": "BUY"})
    assert storage.update_history("u", "AAPL", "2026-10-09T11:00:00", {"evaluation": {"verdict": "stands"}})
    assert not storage.update_history("u", "KO", "2026-10-09T11:00:00", {"evaluation": {}})
    first, second = storage.load_history("u")
    assert "evaluation" not in first and second["evaluation"] == {"verdict": "stands"}


# ── Planted-error benchmark (offline: checks the cases, not Gemini) ─────────

def test_benchmark_cases_select_their_skills_and_unscreened_errors_pass_the_screens():
    from backend import evaluation_benchmark as bench
    for case in bench.SCREENED_CASES + bench.UNSCREENED_CASES:
        name, fixture, edit, expected, _ = case
        ctx, ai = edit(*_load(fixture))
        checks = _checks(ctx, ai)
        assert set(expected) & set(checks), name
        clean = _checks(*_load(fixture))
        new_failures = {(c["skill"], c["check"]) for skill in expected for c in checks.get(skill, []) if not c["passed"]} - {
            (c["skill"], c["check"]) for skill in expected for c in clean.get(skill, []) if not c["passed"]}
        assert bool(new_failures) == (case in bench.SCREENED_CASES), name


# ── Track record calibration ─────────────────────────────────────────────────

def test_calibration_groups_by_verdict_and_compares_brier_scores():
    from backend.track_record import calibration
    def sig(outcome, conf, ret, verdict=None, adj=None):
        return {"outcome": outcome, "confidence": conf, "score_return": ret,
                "evaluation": verdict and {"verdict": verdict, "confidence_adjusted": adj}}
    signals = [sig("Correct", 8, 5.0, "stands", 8), sig("Wrong", 8, -4.0, "weakened", 4),
               sig("Wrong", 6, -2.0), sig("Neutral", 5, 1.0, "stands", 5), sig("Flat", 7, 0.5, "stands", 7), sig("Pending", 7, None, "weakened", 3)]
    cal = calibration(signals)
    groups = {g["verdict"]: g for g in cal["groups"]}
    assert groups["stands"]["n"] == 1 and groups["stands"]["win_rate"] == 100
    assert groups["weakened"]["n"] == 1 and groups["weakened"]["avg_return"] == -4.0
    assert groups["not_evaluated"]["n"] == 1 and groups["contradicted"]["win_rate"] is None
    assert cal["evaluated"] == 2 and cal["lowered"] == 1
    # Lowering confidence on the wrong call improved the score: (0.04 + 0.64) / 2 vs (0.04 + 0.16) / 2.
    assert cal["brier_original"] == pytest.approx(0.34) and cal["brier_adjusted"] == pytest.approx(0.10)


# ── Track record scoring ─────────────────────────────────────────────────────

def _closes(start: str, values: list[float]) -> pd.Series:
    return pd.Series(values, index=pd.bdate_range(start, periods=len(values)), dtype=float)


def test_outcome_is_measured_against_the_benchmark_with_a_flat_band():
    from backend.track_record import _outcome
    assert _outcome("BUY", 3.0) == (3.0, "Correct")
    assert _outcome("BUY", -0.5) == (-0.5, "Flat")
    assert _outcome("SELL", 3.0) == (-3.0, "Wrong")  # the stock beat the market after a SELL
    assert _outcome("SELL", -3.0) == (3.0, "Correct")
    assert _outcome("HOLD", 3.0) == (3.0, "Neutral")
    assert _outcome("BUY", None) == (None, "Pending")


def test_entry_is_the_first_new_york_close_after_the_signal(monkeypatch):
    from backend import track_record as tr
    monkeypatch.setattr(tr, "LOCAL_TZ", timezone(timedelta(hours=8)))  # Singapore
    closes = _closes("2026-10-05", [1, 2, 3, 4, 5])  # Mon 5 – Fri 9 October
    def entry_day(ts):
        return closes.index[tr._entry_index(closes, ts)].day
    assert entry_day("2026-10-07T11:00:00") == 7  # Tue 23:00 in New York, after Tuesday's close
    assert entry_day("2026-10-07T22:00:00") == 7  # Wed 10:00, market open
    assert entry_day("2026-10-08T05:00:00") == 8  # Wed 17:00, after Wednesday's close


def test_score_uses_checkpoints_and_rescales_targets_only_through_splits(monkeypatch):
    from backend import track_record as tr
    monkeypatch.setattr(tr, "LOCAL_TZ", timezone.utc)
    monkeypatch.setattr(tr, "CHECKPOINTS", {2: "2D", 10: "10D"})
    monkeypatch.setattr(tr, "TARGET_DAYS", 3)
    # Split-adjusted closes: a 2-for-1 split means the quoted 200 is 100 here.
    stock = _closes("2026-01-05", [100, 104, 110, 120, 90, 95])
    bench = _closes("2026-01-05", [50, 50, 51, 51, 51, 51])
    rec = {"timestamp": "2026-01-05T10:00:00", "recommendation": "BUY", "price_at_signal": 200, "price_target": 230}
    out = tr._score(rec, stock, bench, current=None, bench_now=None)
    assert out["entry_price"] == 100 and out["entry_date"] == "2026-01-05" and out["split_factor"] == 2
    two_day, ten_day = out["checkpoints"]
    assert two_day["stock"] == pytest.approx(10) and two_day["excess"] == pytest.approx(8)
    assert ten_day["excess"] is None  # not reached yet
    assert out["target"] == {"price": 115, "hit": True, "date": "2026-01-08"}
    assert out["path"][0][1:] == [1, 1] and out["path"][-1][1] == pytest.approx(0.95)
    signal = {"recommendation": "BUY", "checkpoints": out["checkpoints"]}
    assert tr.scored(signal, 2) == (pytest.approx(8), "Correct")
    assert tr.scored(signal, 10) == (None, "Pending")
    # A stale quote 10% off the close is not a split: the target stays as stated.
    stale = tr._score({**rec, "price_at_signal": 90, "price_target": 104}, stock, bench, None, None)
    assert stale["target"]["price"] == 104 and stale["target"]["hit"] is True and stale["split_factor"] == 1


def test_score_without_history_keeps_the_quoted_return_unscored():
    from backend import track_record as tr
    rec = {"timestamp": "2026-01-05T10:00:00", "recommendation": "BUY", "price_at_signal": 100}
    out = tr._score(rec, None, None, current=110, bench_now=None)
    assert out["return_pct"] == pytest.approx(10) and out["checkpoints"] == [] and out["entry_date"] is None


def test_rules_are_scored_on_the_same_calls_as_the_ai():
    from backend import track_record as tr
    sig = {"momentum": -0.2}
    assert tr.rule_calls(sig, {"analyst": "strong_buy", "app_score": 40}) == {
        "always_buy": "BUY", "momentum": "SELL", "analyst": "BUY", "app_score": "SELL"}
    assert tr.rule_calls({"momentum": None}, None) == {"always_buy": "BUY", "momentum": None, "analyst": None, "app_score": None}

    def s(rec, excess, momentum):
        return {"recommendation": rec, "score_excess": excess, "rules": tr.rule_calls({"momentum": momentum}, None)}
    # The stock lagged the market: the AI's SELL was right, always-BUY and positive momentum were wrong.
    cmp = tr.compare_rules([s("SELL", -5.0, 0.3), s("HOLD", 4.0, -0.1), s("BUY", None, 0.2)])
    rows = {r["key"]: r for r in cmp["rows"]}
    assert cmp["checked"] == 2
    assert rows["ai"] == {"key": "ai", "label": "AI", "calls": 1, "win_rate": 100, "avg_return": 5.0}
    assert rows["always_buy"]["calls"] == 2 and rows["always_buy"]["win_rate"] == 50 and rows["always_buy"]["avg_return"] == pytest.approx(-0.5)
    assert rows["momentum"]["win_rate"] == 0  # BUY into a lagging stock, SELL into a leading one
    assert rows["analyst"]["calls"] == 0 and rows["analyst"]["win_rate"] is None


def test_prompt_defines_the_call_the_way_it_is_scored():
    from backend import assessment
    ctx, _ = _load("aapl")
    prompt = assessment._prompt(ctx)
    assert "beat the S&P 500 by more than 1 percentage point" in prompt and "7 = 70%" in prompt
    assert "Medium-term about 1 year" in prompt
    inputs = assessment.rule_inputs(ctx)
    assert inputs["analyst"] == "buy" and 60 < inputs["app_score"] < 70


def test_inputs_are_appended_one_line_per_call(tmp_path, monkeypatch):
    from backend import storage
    monkeypatch.setattr(storage, "DATA_DIR", str(tmp_path))
    assert storage.load_inputs("u") == []
    storage.append_inputs("u", {"timestamp": "t1", "prompt": "a"})
    storage.append_inputs("u", {"timestamp": "t2", "prompt": "b"})
    assert [r["timestamp"] for r in storage.load_inputs("u")] == ["t1", "t2"]


def test_models_are_compared_on_paired_calls():
    from backend import track_record as tr

    def s(model, provider, rec, excess, run=None, symbol="AAPL"):
        return {"model": model, "provider": provider, "recommendation": rec, "score_excess": excess, "run": run, "symbol": symbol}
    signals = [
        s("qwen", "local", "BUY", 4.0, "r1"), s("gemini", "gemini", "SELL", 4.0, "r1"),  # disagree; qwen right
        s("qwen", "local", "BUY", None, "r1", "KO"), s("gemini", "gemini", "BUY", None, "r1", "KO"),  # agree; not scored yet
        s("qwen", "local", "SELL", -3.0, "r2", "MSFT"),  # local only, no pair
    ]
    m = tr.compare_models(signals)
    assert m["pairs"] == 2 and m["agreement"] == 50 and m["pairs_checked"] == 1
    paired = {r["model"]: r for r in m["paired"]}
    assert paired["qwen"]["win_rate"] == 100 and paired["gemini"]["win_rate"] == 0
    assert {r["model"]: r["calls"] for r in m["all"]} == {"gemini": 1, "qwen": 2}


def test_batch_compares_models_only_in_the_last_week():
    from datetime import date
    from backend import batch
    assert batch.providers_for("auto", date(2026, 10, 23)) == ["local"]
    assert batch.providers_for("auto", date(2026, 10, 26)) == ["local", "gemini"]
    assert batch.providers_for("auto", date(2026, 2, 23)) == ["local", "gemini"]  # 28-day month
    assert batch.providers_for("gemini", date(2026, 10, 5)) == ["gemini"]
