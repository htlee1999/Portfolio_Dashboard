"""Removes personal details from text before it goes to Gemini, and puts them back in the reply.

Each distinct value becomes a placeholder such as ``[email-1]``; the same value always gets the same
placeholder within one request, so the model can still refer to it, and ``restore`` swaps the
originals back into the answer before the user sees it. Nothing is redacted for the local model.

Two levels:

- ``strict`` (assessment and evaluation prompts, built from market data): only patterns that can't
  be mistaken for a figure — emails, API keys and passwords, card numbers (Luhn-checked), IBANs
  (checksum-checked), NRIC/FIN and SSNs — plus the user's own hidden words.
- full (chat, where the user types freely): also phone numbers, street and unit addresses, postal
  codes, bank account numbers, dates of birth and IP addresses; and with portfolio privacy on, share
  counts and amounts tied to the user ("I bought at $120", "my net worth is 300k").

Names can't be found reliably by pattern, so users list their own (name, employer, address) under
Settings → AI Privacy, and those are always hidden.
"""

import re
from collections.abc import Callable
from dataclasses import dataclass, field


def _luhn(digits: str) -> bool:
    d = [int(c) for c in re.sub(r"\D", "", digits)]
    if not 13 <= len(d) <= 19:
        return False
    total = sum(d[-1::-2]) + sum(sum(divmod(2 * x, 10)) for x in d[-2::-2])
    return total % 10 == 0


def _iban(value: str) -> bool:
    s = re.sub(r"\s", "", value).upper()
    s = s[4:] + s[:4]
    return int("".join(str(int(c, 36)) for c in s)) % 97 == 1


@dataclass(frozen=True)
class Rule:
    kind: str
    label: str
    pattern: re.Pattern
    strict: bool = False  # safe on market-data prompts
    portfolio: bool = False  # only with portfolio privacy on
    group: int = 0  # the part of the match to hide; the rest (a keyword) stays for context
    check: Callable[[str], bool] | None = None


_MONEY = r"(?:(?:US|S|A|C|HK)?\$|[€£¥]|(?:USD|SGD|EUR|GBP|HKD|JPY|AUD|CAD)\s?)?\d[\d,]*(?:\.\d+)?(?:\s?(?:k|K|m|M|million|thousand|mil)\b)?"

RULES: list[Rule] = [
    Rule("email", "email address", re.compile(r"\b[\w.%+-]+@[\w-]+(?:\.[\w-]+)*\.[A-Za-z]{2,}\b"), strict=True),
    Rule("secret", "API key or password", re.compile(
        r"\b(?:AIza[\w-]{35}|sk-(?:ant-)?[\w-]{20,}|gh[pousr]_\w{30,}|github_pat_\w{30,}|xox[abpr]-[\w-]{10,}"
        r"|AKIA[0-9A-Z]{16}|eyJ[\w-]{10,}\.[\w-]{10,}\.[\w-]{10,})"), strict=True),
    Rule("secret", "API key or password", re.compile(
        r"\b(?:password|passwd|pwd|passcode|pin|api[ _-]?key|secret|token)\b\s*(?:is|:|=)\s*[\"']?([^\s\"']{4,})", re.I),
        strict=True, group=1, check=lambda v: bool(re.search(r"[\d\W_]", v.rstrip(".,;:!?)")))),  # "the token is cheap" stays
    # Grouped as printed on a card; safe on prompts, where long figures are never grouped this way.
    Rule("card", "card number", re.compile(r"\b\d{4}[ -]\d{4,6}[ -]\d{4,5}(?:[ -]\d{1,7})?\b"), strict=True, check=_luhn),
    Rule("card", "card number", re.compile(r"\b[2-6]\d{12,18}\b"), check=_luhn),
    Rule("iban", "bank account (IBAN)", re.compile(r"\b[A-Z]{2}\d{2}(?: ?[A-Z0-9]{4}){2,7}(?: ?[A-Z0-9]{1,4})?\b"),
         strict=True, check=_iban),
    Rule("id", "ID number", re.compile(r"\b[STFGM]\d{7}[A-Z]\b", re.I), strict=True),  # Singapore NRIC / FIN
    Rule("id", "ID number", re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), strict=True),  # US SSN
    Rule("id", "ID number", re.compile(r"\b(?:passport|licen[cs]e|NRIC|FIN|SSN|IC)\s*(?:no\.?|number|#)?\s*(?:is|:)?\s*([A-Z0-9]{6,12})\b", re.I),
         group=1),
    Rule("account", "account number", re.compile(
        r"\b(?:account|acct|a/c)\s*(?:no\.?|number|#)?\s*(?:is|:)?\s*(\d[\d -]{5,}\d)\b", re.I), group=1),
    Rule("phone", "phone number", re.compile(
        r"(?<![\w$])(?:\+\d{1,3}[ -]?)(?:\(?\d{1,4}\)?[ -]?){2,4}\d{2,4}\b"  # international, with +
        r"|(?<![\w$.])\(?\d{3}\)?[ .-]\d{3}[ .-]\d{4}\b"  # US
        r"|(?<![\w$.,])[3689]\d{3}[ -]\d{4}\b")),  # Singapore, split 4-4
    Rule("phone", "phone number", re.compile(
        r"\b(?:phone|mobile|cell|tel|hp|whatsapp|call me(?: at| on)?)\s*(?:no\.?|number|#)?\s*(?:is|:)?\s*(\+?\d[\d -]{6,}\d)\b", re.I),
        group=1),
    Rule("address", "address", re.compile(
        r"\b\d{1,5}[A-Z]?\s+(?:[A-Z][a-z]+\s+){1,4}(?:Street|St|Road|Rd|Avenue|Ave|Drive|Dr|Lane|Ln|Boulevard|Blvd|Way|"
        r"Crescent|Cres|Close|Walk|Place|Pl|Court|Ct|Terrace|Rise|Link|Central|North|South|East|West)\b\.?"
        r"(?:,?\s*#\d{1,3}-\d{1,5})?")),
    Rule("address", "address", re.compile(r"#\d{1,3}-\d{1,5}\b")),  # unit number
    Rule("address", "address", re.compile(r"\b(?:Singapore|S)\s?\(?(\d{6})\)?(?!\d)"), group=1),  # postal code
    Rule("dob", "date of birth", re.compile(
        r"\b(?:born(?: on| in)?|DOB|date of birth|birthday(?: is)?)\s*:?\s*"
        r"(\d{1,2}[ /.-](?:\d{1,2}|[A-Za-z]{3,9})[ /.-]\d{2,4}|[A-Za-z]{3,9} \d{1,2},? \d{4}|\d{4}-\d{2}-\d{2})", re.I), group=1),
    Rule("ip", "IP address", re.compile(r"\b(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)\b")),
    Rule("holding", "position or money figure", re.compile(
        r"\b(\d[\d,]*(?:\.\d+)?)\s*(?:shares?|units?|lots?)\b", re.I), portfolio=True, group=1),
    Rule("holding", "position or money figure", re.compile(
        r"\b(?:I|my|we|our)\b[^.?!\n]{0,40}?\b(?:worth|invested|bought|paid|own|hold|holding|cost basis|average cost|avg cost|"
        r"salary|income|net worth|savings|balance|portfolio(?: is| of)?|put in|lost|made|profit)\b"
        r"\s*(?:(?:it|them|is|was|of|at|for|about|around|roughly|approximately|~|:)\s*){0,3}(" + _MONEY + r")", re.I),
        portfolio=True, group=1),
]


_PLURAL = {"address": "addresses", "email address": "email addresses", "IP address": "IP addresses", "API key or password": "API keys or passwords", "bank account (IBAN)": "bank accounts (IBAN)",
           "date of birth": "dates of birth", "position or money figure": "positions or money figures",
           "word you chose to hide": "words you chose to hide"}


@dataclass
class Redactor:
    terms: list[str] = field(default_factory=list)  # the user's own words to hide, always
    strict: bool = False
    portfolio: bool = False
    _tokens: dict[str, str] = field(default_factory=dict)  # original -> placeholder
    _kinds: dict[str, str] = field(default_factory=dict)  # placeholder -> label

    def _token(self, value: str, kind: str, label: str) -> str:
        if value not in self._tokens:
            n = sum(1 for t in self._tokens.values() if t.startswith(f"[{kind}-")) + 1
            self._tokens[value] = f"[{kind}-{n}]"
            self._kinds[self._tokens[value]] = label
        return self._tokens[value]

    def __call__(self, text: str) -> str:
        if not text:
            return text
        for term in sorted({t.strip() for t in self.terms if len(t.strip()) >= 2}, key=len, reverse=True):
            text = re.sub(rf"(?<!\w){re.escape(term)}(?!\w)",
                          lambda m: self._token(m.group(0), "private", "word you chose to hide"), text, flags=re.I)
        for rule in RULES:
            if (self.strict and not rule.strict) or (rule.portfolio and not self.portfolio):
                continue
            text = rule.pattern.sub(lambda m, r=rule: self._hide(m, r), text)
        return text

    def _hide(self, m: re.Match, rule: Rule) -> str:
        value = m.group(rule.group)
        if not value or (rule.check and not rule.check(value)) or re.fullmatch(r"\[\w+-\d+\]", value):
            return m.group(0)
        start, end = m.start(rule.group) - m.start(), m.end(rule.group) - m.start()
        whole = m.group(0)
        return whole[:start] + self._token(value, rule.kind, rule.label) + whole[end:]

    def restore(self, value):
        """``value`` (text, or lists and dicts of it) with the originals back in place of placeholders."""
        if isinstance(value, str):
            for original, token in self._tokens.items():
                value = value.replace(token, original)
            return value
        if isinstance(value, list):
            return [self.restore(v) for v in value]
        if isinstance(value, dict):
            return {k: self.restore(v) for k, v in value.items()}
        return value

    def found(self) -> list[dict]:
        """What was hidden, by kind: ``[{label, count, text}]``, ``text`` reading like "2 phone numbers"."""
        counts: dict[str, int] = {}
        for label in self._kinds.values():
            counts[label] = counts.get(label, 0) + 1
        return [{"label": k, "count": n, "text": f"{n} {k if n == 1 else _PLURAL.get(k, k + 's')}"} for k, n in counts.items()]
