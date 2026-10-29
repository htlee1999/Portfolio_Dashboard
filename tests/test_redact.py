"""Personal details are hidden from Gemini and put back in its answer; market figures are left alone.
No network.

Run with: PYTHONPATH=. pytest tests
"""

import json

import pytest

from backend import chat, privacy, usage
from backend.redact import Redactor


@pytest.mark.parametrize("text,secret", [
    ("mail me at jane.tan@example.com", "jane.tan@example.com"),
    ("my number is +65 9123 4567", "+65 9123 4567"),
    ("call 9876 5432 tonight", "9876 5432"),
    ("US office (555) 123-4567", "(555) 123-4567"),
    ("NRIC S1234567D", "S1234567D"),
    ("SSN 123-45-6789", "123-45-6789"),
    ("card 4111 1111 1111 1111", "4111 1111 1111 1111"),
    ("card 4111111111111111", "4111111111111111"),
    ("IBAN GB82 WEST 1234 5698 7654 32", "GB82 WEST 1234 5698 7654 32"),
    ("key AIzaSyA1234567890abcdefghijklmnopqrstuv", "AIzaSyA1234567890abcdefghijklmnopqrstuv"),
    ("my password: hunter2!", "hunter2!"),
    ("account number 123-456-789", "123-456-789"),
    ("I live at 12 Orchard Road #05-123", "12 Orchard Road #05-123"),
    ("postal Singapore 238823", "238823"),
    ("DOB: 12/03/1999", "12/03/1999"),
    ("from 192.168.1.20", "192.168.1.20"),
])
def test_hides_personal_details(text, secret):
    r = Redactor()
    hidden = r(text)
    assert secret not in hidden and "[" in hidden
    assert r.restore(hidden) == text


@pytest.mark.parametrize("text", [
    "Is the S&P 500 up 2.5% this year? NVDA trades at 120.5 with RSI 61 and volume 1,234,567.",
    "Report on 2026-10-29; target $250, P/E 31.2, market cap 3,456,789,012,345.",
    "Card 4111 1111 1111 1112 fails the Luhn check.",  # not a real card number
    "the token is cheap",
])
def test_leaves_market_text_alone(text):
    assert Redactor(portfolio=True)(text) == text


def test_portfolio_figures_only_with_privacy_on():
    text = "I own 500 shares of NVDA, bought at $120.50; my portfolio is worth 300k."
    assert Redactor(portfolio=False)(text) == text
    hidden = Redactor(portfolio=True)(text)
    assert not any(x in hidden for x in ("500", "120.50", "300k")) and "NVDA" in hidden


def test_hidden_words_whole_word_any_case():
    r = Redactor(terms=["Jane Tan", "Acme"])
    assert r("jane tan works at ACME, not Acmeville") == "[private-1] works at [private-2], not Acmeville"


def test_same_value_same_placeholder_and_summary():
    r = Redactor()
    out = r("a@b.co and a@b.co, c@d.co")
    assert out == "[email-1] and [email-1], [email-2]"
    assert r.found() == [{"label": "email address", "count": 2, "text": "2 email addresses"}]


def test_strict_skips_patterns_that_look_like_figures():
    text = "Revenue 9123 4567 and 394328000000; contact x@y.com"
    assert Redactor(strict=True)(text) == "Revenue 9123 4567 and 394328000000; contact [email-1]"


def test_gemini_chat_sends_placeholders_and_shows_originals(monkeypatch):
    monkeypatch.setattr(privacy, "gemini_private", lambda u: True)
    monkeypatch.setattr(privacy, "private_terms", lambda u: ["Jane Tan"])
    monkeypatch.setattr(privacy, "get_email", lambda u: None)
    monkeypatch.setattr(usage, "log_call", lambda *a, **k: None)
    sent = {}

    def stub(username, system, messages, tools, cache):
        sent["text"] = system + messages[-1]["content"]
        yield {"type": "text", "text": "Noted, [private-1]; I won't use [phone-1]."}
        yield {"type": "_usage", "input": 0, "output": 0, "text": ""}

    monkeypatch.setitem(chat.PROVIDERS, "gemini", stub)
    msg = [{"role": "user", "content": "I'm Jane Tan, phone 9123 4567. How is AAPL?"}]
    events = [json.loads(line) for line in chat.reply("someone", "gemini", msg, {"path": "/technical", "text": ""})]
    assert "Jane Tan" not in sent["text"] and "9123 4567" not in sent["text"] and "AAPL" in sent["text"]
    assert events[0]["type"] == "redacted"
    assert {e["text"] for e in events[0]["items"]} == {"1 word you chose to hide", "1 phone number"}
    assert events[1] == {"type": "text", "text": "Noted, Jane Tan; I won't use 9123 4567."}

    # The local model gets the message as typed.
    monkeypatch.setitem(chat.PROVIDERS, "local", stub)
    list(chat.reply("someone", "local", msg, {"path": "/technical", "text": ""}))
    assert "Jane Tan" in sent["text"]
