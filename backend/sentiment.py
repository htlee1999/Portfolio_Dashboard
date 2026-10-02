"""News sentiment via SERPapi (Google Finance + Google News), VADER and TextBlob."""

import requests

from config import SENTIMENT_AVAILABLE, get_serp_api_key, is_serp_api_configured

from . import market

if SENTIMENT_AVAILABLE:
    from nltk.sentiment.vader import SentimentIntensityAnalyzer
    from serpapi import GoogleSearch
    from textblob import TextBlob

    _sia = SentimentIntensityAnalyzer()


def status() -> dict:
    return {
        "libraries": SENTIMENT_AVAILABLE,
        "api_key": is_serp_api_configured(),
        "enabled": SENTIMENT_AVAILABLE and is_serp_api_configured(),
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


def _google_finance(symbol: str, limit: int) -> list[dict]:
    exchange = (market.info(symbol) or {}).get("exchange", "NASDAQ")
    results = GoogleSearch({"api_key": get_serp_api_key(), "engine": "google_finance",
                            "q": f"{symbol}:{exchange}"}).get_dict()
    return [
        {"title": i.get("title", ""), "snippet": i.get("snippet", ""),
         "source": i.get("source", "Unknown"), "date": i.get("date", ""),
         "link": i.get("link", ""), "origin": "Google Finance"}
        for i in results.get("news_results", [])[:limit]
        if i.get("title")
    ]


def _google_news(symbol: str, limit: int) -> list[dict]:
    results = GoogleSearch({"api_key": get_serp_api_key(), "engine": "google_news",
                            "q": f"{symbol} stock", "gl": "us", "hl": "en"}).get_dict()
    articles = []
    for i in results.get("news_results", [])[:limit]:
        source = i.get("source")
        articles.append({
            "title": i.get("title", ""), "snippet": i.get("snippet", ""),
            "source": source.get("name", "Unknown") if isinstance(source, dict) else (source or "Unknown"),
            "date": i.get("date", ""), "link": i.get("link", ""), "origin": "Google News",
        })
    return [a for a in articles if a["title"]]


def _label(compound: float) -> str:
    return "Positive" if compound >= 0.05 else "Negative" if compound <= -0.05 else "Neutral"


def analyze(symbol: str, num_articles: int = 20, source: str = "both") -> dict:
    if not status()["enabled"]:
        raise RuntimeError("Sentiment analysis is not configured (needs SERP_API_KEY and NLP libraries).")

    fetched, errors = [], []
    if source in ("finance", "both"):
        try:
            fetched += _google_finance(symbol, num_articles)
        except Exception as e:
            errors.append(f"Google Finance: {e}")
    if source in ("news", "both"):
        try:
            fetched += _google_news(symbol, num_articles)
        except Exception as e:
            errors.append(f"Google News: {e}")

    seen, articles = set(), []
    for a in fetched:
        if a["title"] in seen:
            continue
        seen.add(a["title"])
        text = f"{a['title']} {a['snippet']}"
        vader = _sia.polarity_scores(text)
        blob = TextBlob(text).sentiment
        articles.append({
            **a,
            "vader": vader["compound"],
            "vader_pos": vader["pos"], "vader_neg": vader["neg"], "vader_neu": vader["neu"],
            "polarity": blob.polarity,
            "subjectivity": blob.subjectivity,
            "sentiment": _label(vader["compound"]),
        })

    total = len(articles)
    counts = {k: sum(1 for a in articles if a["sentiment"] == k) for k in ("Positive", "Neutral", "Negative")}
    avg_vader = sum(a["vader"] for a in articles) / total if total else 0.0
    avg_polarity = sum(a["polarity"] for a in articles) / total if total else 0.0
    return {
        "symbol": symbol,
        "overall": _label(avg_vader) if total else None,
        "avg_vader": avg_vader,
        "avg_polarity": avg_polarity,
        "counts": counts,
        "pct": {k: (v / total * 100 if total else 0.0) for k, v in counts.items()},
        "total": total,
        "articles": articles,
        "errors": errors,
        "searches_used": (source == "both") + 1,
    }
