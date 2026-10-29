"""Page-aware chat. The model sees what's on the user's current page and can call the app's
analyses (technicals, fundamentals, forecast, sentiment, portfolio, past assessments) as tools.

Runs on the local model through Ollama by default, or on Gemini. Replies stream as events:
``{"type": "tool", "name", "args"}`` when an analysis runs, ``{"type": "text", "text"}`` for
answer text, then ``{"type": "done", "model"}`` or ``{"type": "error", "message"}``.
"""

import json
import re
from collections.abc import Callable, Iterator

import requests

from config import (GEMINI_AVAILABLE, ML_AVAILABLE, get_gemini_api_key, get_ollama_model, get_ollama_url,
                    is_gemini_api_configured, normalize_symbol)

from . import fundamentals, plan, portfolio, predictive, privacy, returns, risk, sentiment, technical, usage, valuation
from .assessment import MODEL as GEMINI_MODEL
from .storage import load_history, load_settings
from .utils import clean

# Tool rounds before the model must answer with what it has.
MAX_ROUNDS = 4
# Where _gemini counts its API requests in the reply's cache (tool results use tuple keys).
REQUESTS = "_gemini_requests"
# Page text past this is cut; about 3,000 tokens, leaving room for tool results in the local context.
PAGE_CHARS = 12_000
OLLAMA_CONTEXT = 16384
OLLAMA_TIMEOUT = 600

_SYMBOL = re.compile(r"^[A-Za-z0-9.\-^=]{1,20}$")


# ── Tools ────────────────────────────────────────────────────────────────────

def _symbol(args: dict) -> str:
    raw = str(args.get("symbol") or "")
    if not _SYMBOL.match(raw):
        raise ValueError(f"invalid symbol {raw!r}")
    return normalize_symbol(raw)


def _trim(value, limit: int = 600):
    """Long strings (business summaries) cut short, so tool results fit the local model's context."""
    if isinstance(value, str):
        return value if len(value) <= limit else value[:limit] + "…"
    if isinstance(value, dict):
        return {k: _trim(v, limit) for k, v in value.items()}
    if isinstance(value, list):
        return [_trim(v, limit) for v in value]
    return value


def _technicals(username: str, args: dict) -> dict:
    # Always a year: shorter windows leave the 200-day average undefined.
    result = technical.analyze(_symbol(args), "1y", 14, 12, 26, 20, 2.0)
    if result is None:
        raise LookupError("no market data (Yahoo Finance may be rate-limiting)")
    return {k: v for k, v in result.items() if k != "series"}


def _fundamentals(username: str, args: dict) -> dict:
    result = fundamentals.analyze(_symbol(args))
    if result is None:
        raise LookupError("no fundamental data (Yahoo Finance may be rate-limiting)")
    return _trim({k: v for k, v in result.items() if k != "statements"})


def _forecast(username: str, args: dict) -> dict:
    result = predictive.quick(_symbol(args))
    if result is None:
        raise LookupError("not enough price history to test the models")
    return result


def _sentiment(username: str, args: dict) -> dict:
    days = 30 if args.get("days") == 30 else 7
    result = sentiment.analyze(_symbol(args), days, "both")
    out = {k: v for k, v in result.items() if k != "articles"}
    out["headlines"] = [{"title": a["title"], "source": a["source"], "date": a["date"], "sentiment": a["sentiment"]}
                        for a in result["articles"] if a["status"] == "scored"][:10]
    return out


def _portfolio(username: str, args: dict) -> dict:
    m = portfolio.metrics(username, load_settings().get("base_currency", "USD"))
    keep = ("symbol", "quantity", "currency", "purchase_price", "purchase_date", "current_price",
            "value_base", "gain_base", "gain_pct", "weight")
    return {**{k: v for k, v in m.items() if k != "rows"}, "rows": [{k: r.get(k) for k in keep} for r in m["rows"]]}


def _risk(username: str, args: dict) -> dict:
    r = risk.build(username, load_settings().get("base_currency", "USD"))
    keep = ("symbol", "weight", "industry", "vol", "beta", "risk_share", "corr_to_rest")
    return {"portfolio": r.get("portfolio"), "flags": r.get("flags"),
            "holdings": [{k: h.get(k) for k in keep} for h in r.get("holdings", [])],
            "industry": (r.get("exposure") or {}).get("industry", [])[:6],
            "scenarios": [{k: x[k] for k in ("name", "portfolio", "benchmark")} for x in r.get("scenarios", [])]}


def _returns(username: str, args: dict) -> dict:
    r = returns.build(username, load_settings().get("base_currency", "USD"))
    return {k: r.get(k) for k in ("start", "years", "summary", "realized")}


def _valuation(username: str, args: dict) -> dict:
    v = valuation.analyze(_symbol(args), username)
    return {"peer_rows": v["peers"]["rows"], "peers": [p["symbol"] for p in v["peers"]["peers"]], "anchor": v["anchor"]}


def _plan(username: str, args: dict) -> dict:
    s = plan.status(username, load_settings().get("base_currency", "USD"))
    return {"needs_attention": s["triggered"], "earnings_calendar": s["calendar"][:10],
            "rebalance": [r for r in s["rebalance"] if r["target"] is not None],
            "theses": {h["symbol"]: h["thesis"] for h in s["holdings"] if h["thesis"]}}


def _assessments(username: str, args: dict) -> dict:
    history = load_history(username)
    if args.get("symbol"):
        symbol = _symbol(args)
        history = [h for h in history if h.get("symbol") == symbol]
    keep = ("timestamp", "symbol", "recommendation", "confidence", "time_horizon", "price_at_signal",
            "price_target", "reasoning", "position_advice", "model", "source")
    return {"count": len(history), "latest": [{k: h.get(k) for k in keep} for h in history[-5:][::-1]]}


_SYMBOL_PARAM = {"symbol": {"type": "string", "description": "Ticker, e.g. AAPL or D05.SI"}}

# name -> (description, JSON-schema properties, required, function)
_TOOLS: dict[str, tuple[str, dict, list[str], Callable[[str, dict], dict]]] = {
    "get_technicals": (
        "Price, RSI, MACD, Bollinger bands, moving averages, ADX, ATR and momentum for a stock.",
        _SYMBOL_PARAM, ["symbol"], _technicals),
    "get_fundamentals": (
        "Company profile, valuation and profitability ratios, balance-sheet quality, Piotroski F-score, "
        "earnings surprises and estimates, analyst consensus and targets, and ratios against the company's own history.",
        _SYMBOL_PARAM, ["symbol"], _fundamentals),
    "get_forecast": (
        "Machine-learning forecasts of the next session's return, tested walk-forward against a no-change forecast, "
        "and a GARCH volatility range. Takes several seconds.",
        _SYMBOL_PARAM, ["symbol"], _forecast),
    "get_news_sentiment": (
        "Tone of recent news headlines about a stock. Uses paid search credits: call it only when the user asks about news or sentiment.",
        {**_SYMBOL_PARAM, "days": {"type": "integer", "enum": [7, 30]}},
        ["symbol"], _sentiment),
    "get_portfolio": (
        "The user's holdings: quantity, cost, current value, gain and portfolio weight of each, and totals in their base currency.",
        {}, [], _portfolio),
    "get_portfolio_risk": (
        "Portfolio risk: volatility, beta, drawdown, value at risk, effective number of independent bets, each holding's "
        "share of the risk and correlation with the rest, industry concentration, warnings and historical stress tests.",
        {}, [], _risk),
    "get_actual_returns": (
        "The user's actual returns from their purchases, sales and dividends: time and money-weighted returns, the same "
        "trades made in the S&P 500, realized gains and dividend income.",
        {}, [], _returns),
    "get_valuation_anchors": (
        "A stock's multiples against its industry peers, the growth its price implies (reverse DCF), and its earnings "
        "and cash-flow yields against the 10-year Treasury.",
        _SYMBOL_PARAM, ["symbol"], _valuation),
    "get_plan": (
        "The user's plan: alerts that need attention, upcoming earnings for holdings and watchlist, target weights and "
        "the trades to rebalance, and the thesis written for each holding.",
        {}, [], _plan),
    "get_past_assessments": (
        "The latest AI BUY/HOLD/SELL assessments saved in this app, optionally for one symbol.",
        {"symbol": _SYMBOL_PARAM["symbol"]}, [], _assessments),
}


def _available() -> list[str]:
    names = list(_TOOLS)
    if not ML_AVAILABLE:
        names.remove("get_forecast")
    if not sentiment.status()["enabled"]:
        names.remove("get_news_sentiment")
    return names


def _schema(name: str) -> dict:
    description, props, required, _ = _TOOLS[name]
    return {"name": name, "description": description,
            "parameters": {"type": "object", "properties": props, "required": required}}


def _run_tool(username: str, name: str, args: dict, cache: dict) -> dict:
    """The tool's result, or an error the model can read and work around."""
    key = (name, json.dumps(args, sort_keys=True))
    if key not in cache:
        if name not in _TOOLS:
            cache[key] = {"error": f"unknown tool {name}"}
        else:
            try:
                cache[key] = clean(_TOOLS[name][3](username, args or {}))
            except Exception as e:
                cache[key] = {"error": str(e)}
    return cache[key]


# ── Prompt ───────────────────────────────────────────────────────────────────

def _system(page: dict, private: bool = False) -> str:
    text = (page.get("text") or "").strip()
    if len(text) > PAGE_CHARS:
        text = text[:PAGE_CHARS] + "\n[…page text cut short]"
    if private and not privacy.public_page(page.get("path")):
        text = "[withheld: this page shows the user's own data, which they keep private from this model]"
    return "\n".join([
        "You are the assistant inside a personal stock portfolio dashboard. Answer questions about the page the user is "
        "looking at, their portfolio, and the stocks they research.",
        "",
        f"CURRENT PAGE: {page.get('title') or 'untitled'} ({page.get('path') or '/'})",
        f"Selected symbol: {page.get('symbol') or 'none'}",
        "What the page shows (its visible text; charts appear only as their labels):",
        "<page>", text or "(empty)", "</page>",
        "",
        "- Answer from the page when it has what the question needs. When it doesn't (another section, another stock, "
        "or a figure not shown), call the tools yourself before answering; never ask the user for permission to look "
        "something up. \"This stock\" means the selected symbol.",
        "- Never invent numbers. Say when a figure isn't on the page or in a tool result.",
        "- Be concise: a few sentences or a short list. Use Markdown sparingly.",
        "- You can explain what the analyses mean and weigh them, but say clearly that this is not personal financial advice "
        "when the user asks whether to buy or sell.",
        *(["- The user keeps their portfolio private from you: you can't see their holdings, trades, plan or past "
           "assessments. If a question needs them, say so and suggest switching the chat to the local model."]
          if private else []),
    ])


# ── Local model (Ollama) ─────────────────────────────────────────────────────

def _ollama(username: str, system: str, messages: list[dict], tools: list[str], cache: dict) -> Iterator[dict]:
    history = [{"role": "system", "content": system}, *messages]
    spec = [{"type": "function", "function": _schema(n)} for n in tools]
    tokens_in = tokens_out = 0
    answer = ""
    for round_ in range(MAX_ROUNDS + 1):
        body = {"model": get_ollama_model(), "messages": history, "stream": True,
                # Thinking takes minutes on a laptop; a chat reply should come in seconds.
                "think": False, "options": {"num_ctx": OLLAMA_CONTEXT}}
        if round_ < MAX_ROUNDS and spec:
            body["tools"] = spec
        try:
            r = requests.post(f"{get_ollama_url()}/api/chat", json=body, stream=True, timeout=OLLAMA_TIMEOUT)
        except requests.ConnectionError as e:
            raise RuntimeError(f"Ollama isn't running at {get_ollama_url()}; start the Ollama app") from e
        if r.status_code != 200:
            raise RuntimeError(f"Ollama returned {r.status_code}: {r.text[:200]}")

        content, calls = "", []
        for line in r.iter_lines():
            if not line:
                continue
            chunk = json.loads(line)
            if chunk.get("error"):
                raise RuntimeError(chunk["error"])
            msg = chunk.get("message") or {}
            if msg.get("content"):
                content += msg["content"]
                yield {"type": "text", "text": msg["content"]}
            calls += msg.get("tool_calls") or []
            if chunk.get("done"):
                tokens_in += chunk.get("prompt_eval_count") or 0
                tokens_out += chunk.get("eval_count") or 0
        answer += content
        if not calls:
            break
        history.append({"role": "assistant", "content": content, "tool_calls": calls})
        for call in calls:
            fn = call["function"]
            args = fn.get("arguments") or {}
            yield {"type": "tool", "name": fn["name"], "args": args}
            history.append({"role": "tool", "tool_name": fn["name"],
                            "content": json.dumps(_run_tool(username, fn["name"], args, cache))})
    yield {"type": "_usage", "input": tokens_in, "output": tokens_out, "text": answer}


# ── Gemini ───────────────────────────────────────────────────────────────────

def _gemini(username: str, system: str, messages: list[dict], tools: list[str], cache: dict) -> Iterator[dict]:
    if not GEMINI_AVAILABLE:
        raise RuntimeError("The google-genai package is not installed.")
    if not is_gemini_api_configured():
        raise RuntimeError("GEMINI_API_KEY is not configured in .env.")
    from google import genai

    client = genai.Client(api_key=get_gemini_api_key())
    contents = [{"role": "model" if m["role"] == "assistant" else "user", "parts": [{"text": m["content"]}]}
                for m in messages]
    declarations = [{"name": s["name"], "description": s["description"], "parameters_json_schema": s["parameters"]}
                    for s in map(_schema, tools)]
    tokens_in = tokens_out = prompt_tokens = 0
    answer = ""
    for round_ in range(MAX_ROUNDS + 1):
        config = {"system_instruction": system, "thinking_config": {"thinking_level": "low"},
                  "automatic_function_calling": {"disable": True}}
        if declarations:
            config["tools"] = [{"function_declarations": declarations}]
            # The last round must answer; earlier tool calls stay in the history either way.
            config["tool_config"] = {"function_calling_config": {"mode": "AUTO" if round_ < MAX_ROUNDS else "NONE"}}
        # Each round is its own request against the limits; the prompt grows with every tool result.
        usage.acquire(prompt_tokens or usage.estimate_tokens(system + json.dumps(messages)))
        cache[REQUESTS] = cache.get(REQUESTS, 0) + 1
        response = client.models.generate_content(model=GEMINI_MODEL, contents=contents, config=config)
        meta = getattr(response, "usage_metadata", None)
        if meta:
            prompt_tokens = meta.prompt_token_count or prompt_tokens
            tokens_in += meta.prompt_token_count or 0
            tokens_out += (meta.candidates_token_count or 0) + (meta.thoughts_token_count or 0)
        calls = response.function_calls or []
        if not calls:
            text = response.text or ""
            if not text:
                reason = response.candidates[0].finish_reason if response.candidates else "no candidates"
                raise RuntimeError(f"empty response ({reason})")
            answer += text
            yield {"type": "text", "text": text}
            break
        # The model's turn goes back as it came: Gemini 3 checks the thought signatures in it.
        contents.append(response.candidates[0].content)
        parts = []
        for call in calls:
            args = dict(call.args or {})
            yield {"type": "tool", "name": call.name, "args": args}
            # Only the tools offered run, so a privacy-withheld tool stays shut even if the model names it.
            result = _run_tool(username, call.name, args, cache) if call.name in tools \
                else {"error": f"{call.name} isn't available"}
            parts.append({"function_response": {"name": call.name, "response": {"result": result}}})
        contents.append({"role": "user", "parts": parts})
    yield {"type": "_usage", "input": tokens_in, "output": tokens_out, "text": answer}


# ── Entry points ─────────────────────────────────────────────────────────────

PROVIDERS = {"local": _ollama, "gemini": _gemini}


def model_name(provider: str) -> str:
    return GEMINI_MODEL if provider == "gemini" else get_ollama_model()


def providers() -> dict:
    """Which models can answer, and why not when one can't."""
    try:
        tags = requests.get(f"{get_ollama_url()}/api/tags", timeout=3).json()
        local = None if get_ollama_model() in {m["name"] for m in tags.get("models", [])} \
            else f"{get_ollama_model()} isn't pulled (ollama pull {get_ollama_model()})"
    except requests.RequestException:
        local = f"Ollama isn't running at {get_ollama_url()}"
    gemini = None if GEMINI_AVAILABLE and is_gemini_api_configured() else "GEMINI_API_KEY is not configured"
    return {
        "default": "local",
        "local": {"model": get_ollama_model(), "problem": local},
        "gemini": {"model": GEMINI_MODEL, "problem": gemini},
    }


def reply(username: str, provider: str, messages: list[dict], page: dict) -> Iterator[str]:
    """NDJSON lines answering the last message, with the page as context."""
    private = privacy.is_private(username, provider)
    model = model_name(provider)
    symbol = page.get("symbol") or None
    prompt_log = _system(page, private) + "\n\n" + "\n".join(f"{m['role']}: {m['content']}" for m in messages)
    # Gemini gets personal details as placeholders; the answer gets them back before the user sees it.
    redactor = privacy.redactor(username) if provider == "gemini" else None
    if redactor:
        page = {**page, "title": redactor(page.get("title") or ""), "text": redactor(page.get("text") or "")}
        messages = [{**m, "content": redactor(m["content"])} for m in messages]
        if hidden := redactor.found():
            yield json.dumps({"type": "redacted", "items": hidden}) + "\n"
    system = _system(page, private)
    cache: dict = {}
    try:
        tools = privacy.tools(_available()) if private else _available()
        for event in PROVIDERS[provider](username, system, messages, tools, cache):
            if redactor:
                event = redactor.restore(event)
            if event["type"] == "_usage":
                usage.log_call(model, prompt_log, event["text"], "chat", symbol,
                               input_tokens=event["input"] or None, output_tokens=event["output"] or None,
                               requests=cache.get(REQUESTS))
                continue
            yield json.dumps(event) + "\n"
    except Exception as e:
        usage.log_call(model, prompt_log, "", "chat", symbol, success=False, error_message=str(e),
                       requests=cache.get(REQUESTS))
        yield json.dumps({"type": "error", "message": str(e)}) + "\n"
        return
    yield json.dumps({"type": "done", "model": model}) + "\n"
