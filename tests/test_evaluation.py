"""Skill selection, rule screens and rule enforcement for the assessment evaluation.

Fixtures are real assessment contexts and one-shot results (AAPL and RIVN, October 2026).
Nothing here calls Gemini or the network: the five-year back-test is stubbed.

Run with: PYTHONPATH=. pytest tests
"""

import copy
import json
from pathlib import Path

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


def test_only_current_recent_technical_signals_are_screened():
    ctx, ai = _load("aapl")  # MACD bearish now; the RSI sell signal fired months ago
    failed = _failed(ctx, ai, "technical-evidence")
    assert failed == ["MACD crosses below signal"]


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
