"""News sentiment: recent, firm-specific headlines from SERPapi (Google Finance + Google News),
scored with a language model fine-tuned on financial news (VADER when torch isn't installed).

Headlines are filtered before scoring: older than the window, duplicates of a story already
counted, routine holdings filings and headlines that don't name the company are shown but
excluded. The overall tone is the mean of positive-minus-negative probabilities with a 95%
confidence interval, and only counts as positive or negative when the interval excludes zero.
"""

import importlib.util
import math
import os
import re
import threading
from datetime import datetime, timedelta, timezone

os.environ.setdefault("USE_TF", "0")  # see predictive.py: TensorFlow + torch deadlock on macOS
os.environ.setdefault("USE_FLAX", "0")
os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

import numpy as np
import requests
from scipy import stats

from config import SENTIMENT_AVAILABLE, get_serp_api_key, is_serp_api_configured

from . import market

if SENTIMENT_AVAILABLE:
    from nltk.sentiment.vader import SentimentIntensityAnalyzer
    from serpapi import GoogleSearch

    _sia = SentimentIntensityAnalyzer()

DEFAULT_MODEL = "mrm8488/distilroberta-finetuned-financial-news-sentiment-analysis"
FINANCE_MODEL = os.getenv("SENTIMENT_MODEL", DEFAULT_MODEL)
FINANCE_NAME = "DistilRoBERTa (financial news)" if FINANCE_MODEL == DEFAULT_MODEL else FINANCE_MODEL.split("/")[-1]
MIN_ARTICLES = 5
LABELS = ("Positive", "Neutral", "Negative")


def _finance_installed() -> bool:
    return importlib.util.find_spec("transformers") is not None and importlib.util.find_spec("torch") is not None


def status() -> dict:
    finance = _finance_installed()
    return {
        "libraries": SENTIMENT_AVAILABLE,
        "api_key": is_serp_api_configured(),
        "enabled": SENTIMENT_AVAILABLE and is_serp_api_configured(),
        "scorer": {"finance": finance, "model": FINANCE_MODEL if finance else "VADER",
                   "note": None if finance else "Install torch and transformers to score with the financial-news model"},
    }


def account() -> dict:
    response = requests.get("https://serpapi.com/account", params={"api_key": get_serp_api_key()}, timeout=10)
    response.raise_for_status()
    data = response.json()
    return {
        "plan": data.get("plan_name") or data.get("plan"),
        "searches_left": data.get("total_searches_left"),
        "used_this_month": data.get("this_month_usage"),
        "plan_searches_left": data.get("plan_searches_left"),
        "searches_per_month": data.get("searches_per_month"),
    }


# ── Which company, and how to search for it ──

# Yahoo exchange codes → Google Finance's. Exchanges missing here skip Google Finance.
_GOOGLE_EXCHANGE = {
    "NMS": "NASDAQ", "NGM": "NASDAQ", "NCM": "NASDAQ", "NAS": "NASDAQ",
    "NYQ": "NYSE", "NYS": "NYSE", "ASE": "NYSEAMERICAN", "PCX": "NYSEARCA", "BTS": "BATS",
    "SES": "SGX", "HKG": "HKG", "TOR": "TSE", "LSE": "LON", "ASX": "ASX", "JPX": "TYO", "TYO": "TYO",
    "GER": "ETR", "PAR": "EPA", "AMS": "AMS", "MIL": "BIT", "EBS": "SWX", "NSI": "NSE", "BSE": "BOM",
    "TAI": "TPE", "KSC": "KRX",
}
_SUFFIX = re.compile(r"[\s,]+(inc|incorporated|corp|corporation|co|company|ltd|limited|plc|public limited company"
                     r"|holdings?|n\.?v|s\.?a|ag|se|spa|asa|ab|oyj|\(the\))\.?$", re.I)
_GENERIC = {"the", "first", "american", "united", "general", "international", "national", "global", "new"}
# Names headlines use that differ from the registered name
_ALIASES = {"GOOGL": ["Google"], "GOOG": ["Google"], "TSM": ["TSMC"], "META": ["Facebook", "Instagram"], "BRK-B": ["Buffett"],
            "KO": ["Coke"]}


def _company(symbol: str) -> dict:
    info = market.info(symbol) or {}
    root = symbol.split(".")[0].lstrip("^")
    exchange = _GOOGLE_EXCHANGE.get(info.get("exchange", ""))
    name = info.get("longName") or info.get("shortName") or ""
    name = re.sub(r"^the\s+", "", name, flags=re.I)
    while (stripped := _SUFFIX.sub("", name)) != name:
        name = stripped
    words = name.split()
    keyword = " ".join(words[:2]) if words and words[0].lower() in _GENERIC else (words[0] if words else "")
    is_company = info.get("quoteType", "EQUITY") == "EQUITY" and bool(name)
    google_root = (root.lstrip("0") if exchange == "HKG" else root).replace("-", ".")
    return {
        "name": name or root,
        # Funds and indices have no single company to look for, so every headline counts as relevant
        "keywords": ([keyword] if len(keyword) >= 3 else []) + _ALIASES.get(symbol, []) if is_company else None,
        "ticker": root,
        "google_finance": f"{google_root}:{exchange}" if exchange and not symbol.startswith("^") else None,
        "google_news": f"{name} stock" if is_company else f"{root} ETF" if info.get("quoteType") == "ETF" else name or root,
    }


# ── Fetching ──

_RELATIVE = re.compile(r"(\d+|an?|one)\s+(minute|hour|day|week|month|year)s?\s+ago", re.I)
_UNIT = {"minute": 1 / 1440, "hour": 1 / 24, "day": 1, "week": 7, "month": 30, "year": 365}


def _published(item: dict, now: datetime) -> datetime | None:
    if iso := item.get("iso_date"):
        try:
            return datetime.fromisoformat(iso.replace("Z", "+00:00"))
        except ValueError:
            pass
    if m := _RELATIVE.search(item.get("date") or ""):
        n = 1 if m.group(1).lower() in ("a", "an", "one") else int(m.group(1))
        return now - timedelta(days=n * _UNIT[m.group(2).lower()])
    return None


def _google_finance(query: str, now: datetime) -> list[dict]:
    results = GoogleSearch({"api_key": get_serp_api_key(), "engine": "google_finance", "q": query}).get_dict()
    return [
        # Google Finance puts the headline in `snippet` and has no `title`
        {"title": i.get("title") or i.get("snippet", ""), "source": i.get("source", "Unknown"),
         "date": i.get("date", ""), "published": _published(i, now), "link": i.get("link", ""), "origin": "Google Finance"}
        for i in results.get("news_results", [])
        if i.get("title") or i.get("snippet")
    ]


def _google_news(query: str, now: datetime) -> list[dict]:
    results = GoogleSearch({"api_key": get_serp_api_key(), "engine": "google_news", "q": query,
                            "gl": "us", "hl": "en"}).get_dict()
    articles = []
    for i in results.get("news_results", []):
        # Story clusters carry their articles in `stories` rather than at the top level
        for s in i.get("stories") or [i]:
            source = s.get("source")
            articles.append({
                "title": s.get("title", ""),
                "source": source.get("name", "Unknown") if isinstance(source, dict) else (source or "Unknown"),
                "date": s.get("date", ""), "published": _published(s, now), "link": s.get("link", ""),
                "origin": "Google News",
            })
    return [a for a in articles if a["title"]]


# ── Filtering ──

# Institutional holdings changes (13F filings, reported weeks after the trades) and pre-planned
# insider sales: frequent, formulaic and not new information.
_ROUTINE = re.compile(
    r"\b(stock|shares)\s+(sold|bought|acquired|purchased)\s+by\b"
    r"|\b(llc|l\.?p\.?|inc\.?|ltd\.?|management|advisors?|advisers?|capital|partners|trust|wealth|investments?|"
    r"securities|associates|services|counsel|financial|bank|group|corp\.?|co\.?|na)\s+"
    r"(has|holds|sells|buys|acquires|purchases|trims|lowers|raises|increases|decreases|reduces|boosts|cuts|grows|"
    r"lifts|adds|takes|establishes|initiates|invests|makes)\b.{0,40}\b(position|holdings|stake|shares)\b"
    r"|\bform\s*(4|13f|144)\b|\b13f\b|\b10b5-1\b|\bpreset trading plan\b",
    re.I)
_PRICE_MOVE = re.compile(
    r"\b(rise|rising|rose|jump|jumping|jumped|surge|surging|surged|soar|soaring|soared|climb|climbing|climbed|gain|gaining|"
    r"gained|rall(y|ies|ying|ied)|pop|pops|popped|fall|falling|fell|drop|dropping|dropped|slide|sliding|slid|sink|sinking|sank|"
    r"plunge|plunging|plunged|tumble|tumbling|tumbled|slump|slumping|slumped|dip|dipping|dipped|retreat|retreating|retreated|"
    r"rebound|rebounding|rebounded|slip|slipping|slipped|ticks? (up|down)|edges? (higher|lower)|"
    r"trad(es|ing) (up|down|higher|lower)|(ends?|closes?|finish(es)?) (the day )?(higher|lower))s?\b"
    r"|\b(is|are|up|down|plus|minus) \d+(\.\d+)? ?(%|percent)|\d+(\.\d+)? ?(%|percent) (gain|rise|dip|drop|fall|decline|loss)"
    r"|\b(up|down) today\b|\bis (up|down)\b|\b(record|all-time|yearly|52-week) (high|low)s?\b",
    re.I)


def _words(title: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", title.lower()))


def _mentions(title: str, company: dict) -> bool:
    plain = lambda t: t.lower().replace("-", " ")  # "Coca Cola" and "Coca-Cola" are the same name
    if company["keywords"] is None or any(plain(k) in plain(title) for k in company["keywords"]):
        return True
    tail = r"(?![A-Za-z0-9])" if len(company["ticker"]) <= 2 else r"(?![a-z])"
    return re.search(rf"(?<![A-Za-z0-9]){re.escape(company['ticker'])}{tail}", title) is not None


def _classify(articles: list[dict], company: dict, cutoff: datetime) -> None:
    """Set each article's status: scored, or why it was left out."""
    kept: list[set[str]] = []
    for a in articles:
        words = _words(a["title"])
        if a["published"] is None:
            a["status"] = "undated"
        elif a["published"] < cutoff:
            a["status"] = "old"
        elif any(len(words & k) / max(len(words | k), 1) >= 0.7 for k in kept):
            a["status"] = "duplicate"
        elif _ROUTINE.search(a["title"]):
            a["status"] = "routine"
        elif not _mentions(a["title"], company):
            a["status"] = "off_topic"
        else:
            a["status"] = "scored"
        if a["status"] in ("scored", "routine", "off_topic"):
            kept.append(words)
        a["price_move"] = bool(_PRICE_MOVE.search(a["title"]))


# ── Scoring ──

_model_lock = threading.RLock()
_model = None


def _load_model():
    global _model
    with _model_lock:
        if _model is None:
            import torch
            from transformers import AutoModelForSequenceClassification, AutoTokenizer
            torch.set_num_threads(2)
            tokenizer = AutoTokenizer.from_pretrained(FINANCE_MODEL)
            model = AutoModelForSequenceClassification.from_pretrained(FINANCE_MODEL).eval()
            labels = {i: l.lower() for i, l in model.config.id2label.items()}
            if set(labels.values()) != {"positive", "neutral", "negative"}:
                raise RuntimeError(f"{FINANCE_MODEL} doesn't output positive/neutral/negative labels")
            _model = (tokenizer, model, [labels[i] for i in range(len(labels))])
        return _model


def _score_finance(texts: list[str]) -> list[dict]:
    import torch
    tokenizer, model, labels = _load_model()
    out = []
    with _model_lock, torch.inference_mode():
        for i in range(0, len(texts), 32):
            batch = tokenizer(texts[i:i + 32], padding=True, truncation=True, max_length=64, return_tensors="pt")
            for p in model(**batch).logits.softmax(-1).tolist():
                prob = dict(zip(labels, p))
                label = max(prob, key=prob.get)
                out.append({"sentiment": label.capitalize(), "score": prob["positive"] - prob["negative"],
                            "confidence": prob[label]})
    return out


def _score_vader(texts: list[str]) -> list[dict]:
    out = []
    for t in texts:
        c = _sia.polarity_scores(t)["compound"]
        out.append({"sentiment": "Positive" if c >= 0.05 else "Negative" if c <= -0.05 else "Neutral",
                    "score": c, "confidence": None})
    return out


def _score(texts: list[str]) -> tuple[list[dict], dict, str | None]:
    if _finance_installed():
        try:
            return _score_finance(texts), {"name": FINANCE_NAME, "model": FINANCE_MODEL, "finance": True}, None
        except Exception as e:
            note = f"The financial-news model couldn't load ({e}); scored with VADER instead."
    else:
        note = None
    return _score_vader(texts), {"name": "VADER", "model": "VADER (general-purpose word list)", "finance": False}, note


# ── Summaries ──

def _price_change(symbol: str, days: int) -> dict | None:
    data = market.history(symbol, "3mo")
    if data is None or len(data) < 2:
        return None
    closes = data["Close"].dropna()
    start = closes.index[-1] - timedelta(days=days)
    before = closes[closes.index <= start]
    first = before.iloc[-1] if len(before) else closes.iloc[0]
    first_date = before.index[-1] if len(before) else closes.index[0]
    return {"change_pct": float(closes.iloc[-1] / first - 1) * 100,
            "from": first_date.date().isoformat(), "to": closes.index[-1].date().isoformat()}


def _tone(scores: np.ndarray) -> tuple[float | None, list[float] | None, str | None]:
    """Mean tone, its 95% t-interval, and the label it supports."""
    n = len(scores)
    if n == 0:
        return None, None, None
    mean = float(scores.mean())
    if n < MIN_ARTICLES:
        return mean, None, None
    half = float(stats.t.ppf(0.975, n - 1) * scores.std(ddof=1) / math.sqrt(n))
    ci = [mean - half, mean + half]
    return mean, ci, "Positive" if ci[0] > 0 else "Negative" if ci[1] < 0 else "Neutral"


def analyze(symbol: str, days: int = 7, source: str = "both") -> dict:
    if not status()["enabled"]:
        raise RuntimeError("Sentiment analysis is not configured (needs SERP_API_KEY and NLP libraries).")

    now = datetime.now(timezone.utc)
    company = _company(symbol)
    fetched, errors, searches = [], [], 0
    if source in ("finance", "both"):
        if company["google_finance"]:
            searches += 1
            try:
                fetched += _google_finance(company["google_finance"], now)
            except Exception as e:
                errors.append(f"Google Finance: {e}")
        elif source == "finance":
            errors.append("Google Finance doesn't cover this exchange or symbol type; try Google News.")
    if source in ("news", "both"):
        searches += 1
        try:
            fetched += _google_news(company["google_news"], now)
        except Exception as e:
            errors.append(f"Google News: {e}")

    far_past = datetime.min.replace(tzinfo=timezone.utc)
    articles = sorted(fetched, key=lambda a: a["published"] or far_past, reverse=True)
    _classify(articles, company, now - timedelta(days=days))

    note = None
    if articles:
        scored, scorer, note = _score([a["title"] for a in articles])
        for a, s in zip(articles, scored):
            a.update(s)
    else:
        scorer = {"name": FINANCE_NAME, "model": FINANCE_MODEL, "finance": True} if _finance_installed() \
            else {"name": "VADER", "model": "VADER (general-purpose word list)", "finance": False}

    used = [a for a in articles if a["status"] == "scored"]
    mean, ci, overall = _tone(np.array([a["score"] for a in used]))
    counts = {k: sum(1 for a in used if a["sentiment"] == k) for k in LABELS}

    by_day: dict[str, list[float]] = {}
    for a in used:
        by_day.setdefault(a["published"].date().isoformat(), []).append(a["score"])

    for a in articles:
        a["published"] = a["published"].isoformat() if a["published"] else None

    return {
        "symbol": symbol,
        "days": days,
        "query": company,
        "scorer": scorer,
        "scorer_note": note,
        "overall": overall,
        "index": mean,
        "ci": ci,
        "n": len(used),
        "min_articles": MIN_ARTICLES,
        "counts": counts,
        "pct": {k: (v / len(used) * 100 if used else 0.0) for k, v in counts.items()},
        "excluded": {k: sum(1 for a in articles if a["status"] == k)
                     for k in ("old", "undated", "duplicate", "routine", "off_topic")},
        "price": _price_change(symbol, days),
        "price_move_share": (sum(a["price_move"] for a in used) / len(used)) if used else None,
        "daily": [{"date": d, "n": len(v), "mean": float(np.mean(v))} for d, v in sorted(by_day.items())],
        "articles": articles,
        "errors": errors,
        "searches_used": searches,
    }
