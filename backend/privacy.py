"""Keeps a user's portfolio away from Gemini when they ask for it (Settings → AI Privacy, on by default).

Google may use free-tier Gemini prompts and responses to improve its models, and people may read them.
Market data is public; what's personal is the user's positions, so with privacy on:

- assessments and evaluations on Gemini leave out the position and portfolio sections of the context
  (the call is about the stock either way; only the sizing advice loses its footing);
- Gemini chat gets no tools that read the user's own data, and sees the page's text only on pages
  about a stock's public data.

Separately, whatever the setting, text bound for Gemini goes through backend/redact.py, which hides
personal details (emails, phone numbers, ID and card numbers, keys, addresses, the user's own hidden
words) and restores them in the reply.

The local model always gets everything: it never leaves the machine.
"""

from .auth import gemini_private, get_email, private_terms
from .redact import Redactor

# Context keys holding the user's own data (see assessment.build_context).
PERSONAL_CONTEXT = ("position", "portfolio")

# Chat tools that read the user's own data.
PERSONAL_TOOLS = {"get_portfolio", "get_portfolio_risk", "get_actual_returns", "get_plan", "get_past_assessments"}

# Pages whose text is a stock's public data, by the first part of the path.
PUBLIC_PAGES = {"technical", "fundamentals", "forecast", "sentiment", "retrograde"}


def is_private(username: str, provider: str) -> bool:
    return provider == "gemini" and gemini_private(username)


def context(ctx: dict) -> dict:
    """The assessment context without the user's own data."""
    return {**ctx, **{k: None for k in PERSONAL_CONTEXT}}


def tools(names: list[str]) -> list[str]:
    return [n for n in names if n not in PERSONAL_TOOLS]


def public_page(path: str | None) -> bool:
    return (path or "/").strip("/").split("/")[0].split("?")[0] in PUBLIC_PAGES


def redactor(username: str, strict: bool = False) -> Redactor:
    """Hides personal details from Gemini. ``strict`` for prompts built from market data, where only
    patterns that can't be mistaken for a figure apply."""
    terms = [*private_terms(username), *([e] if (e := get_email(username)) else [])]
    return Redactor(terms=terms, strict=strict, portfolio=gemini_private(username))
