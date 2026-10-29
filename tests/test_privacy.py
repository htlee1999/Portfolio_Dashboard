"""Gemini privacy: with it on, Gemini never sees the user's position, portfolio or private pages.
The local model always sees everything. No network.

Run with: PYTHONPATH=. pytest tests
"""

import json
from pathlib import Path

import pytest

from backend import assessment, chat, privacy, usage

FIXTURES = Path(__file__).parent / "fixtures"

POSITION = {"quantity": 123.0, "avg_cost": 87.65, "currency": "USD", "unrealized_pct": 42.0, "lots": 2}
PORTFOLIO = {"weight": 31.0, "risk_share": 35.0, "corr_to_rest": 0.6, "industry": "Consumer Electronics",
             "industry_weight": 31.0, "largest": [{"symbol": "AAPL", "weight": 31}, {"symbol": "ZZZZ", "weight": 20}],
             "holdings": 9, "effective_bets": 4.2, "beta": 1.1}
PERSONAL = ("CURRENT POSITION", "123.00 shares", "87.65", "PORTFOLIO FIT", "ZZZZ")


@pytest.fixture
def ctx():
    c = json.loads((FIXTURES / "assessment_aapl.json").read_text())["context"]
    return {**c, "position": POSITION, "portfolio": PORTFOLIO}


@pytest.fixture
def private(monkeypatch):
    state = {"on": True}
    monkeypatch.setattr(privacy, "gemini_private", lambda username: state["on"])
    monkeypatch.setattr(privacy, "private_terms", lambda username: [])
    monkeypatch.setattr(privacy, "get_email", lambda username: None)
    monkeypatch.setattr(usage, "log_call", lambda *a, **k: None)
    return state


def _prompt_sent(monkeypatch, ctx, provider):
    sent = {}

    def stub(prompt):
        sent["prompt"] = prompt
        raise RuntimeError("stop")  # nothing to save

    monkeypatch.setitem(assessment.PROVIDERS, provider, stub)
    with pytest.raises(RuntimeError):
        assessment.generate("someone", ctx, provider)
    return sent["prompt"]


def test_gemini_assessment_leaves_out_position_and_portfolio(monkeypatch, ctx, private):
    prompt = _prompt_sent(monkeypatch, ctx, "gemini")
    assert not [p for p in PERSONAL if p in prompt]
    assert "AAPL" in prompt  # still about the stock


def test_local_model_and_privacy_off_keep_everything(monkeypatch, ctx, private):
    assert all(p in _prompt_sent(monkeypatch, ctx, "local") for p in PERSONAL)
    private["on"] = False
    assert all(p in _prompt_sent(monkeypatch, ctx, "gemini") for p in PERSONAL)


def test_context_copy_leaves_original_alone(ctx):
    assert privacy.context(ctx)["position"] is None
    assert ctx["position"] == POSITION


@pytest.mark.parametrize("path,public", [
    ("/technical", True), ("/fundamentals?symbol=AAPL", True), ("/forecast/", True),
    ("/", False), ("/holdings", False), ("/plan", False), ("/settings", False), ("/assessment", False), (None, False),
])
def test_public_pages(path, public):
    assert privacy.public_page(path) is public


def test_gemini_chat_gets_no_personal_tools_or_page(monkeypatch, private):
    seen = {}

    def stub(username, system, messages, tools, cache):
        seen.update(system=system, tools=tools)
        yield {"type": "_usage", "input": 0, "output": 0, "text": ""}

    monkeypatch.setitem(chat.PROVIDERS, "gemini", stub)
    page = {"path": "/holdings", "title": "Holdings", "text": "AAPL 123 shares worth $25,000"}
    list(chat.reply("someone", "gemini", [{"role": "user", "content": "hi"}], page))
    assert not set(seen["tools"]) & privacy.PERSONAL_TOOLS
    assert "get_technicals" in seen["tools"]
    assert "25,000" not in seen["system"] and "private from you" in seen["system"]

    monkeypatch.setitem(chat.PROVIDERS, "local", stub)
    list(chat.reply("someone", "local", [{"role": "user", "content": "hi"}], page))
    assert "get_portfolio" in seen["tools"] and "25,000" in seen["system"]
