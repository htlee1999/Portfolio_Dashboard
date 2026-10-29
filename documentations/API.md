# API reference

The FastAPI server listens on port 8000. The web app reaches it through the same-origin path `/api/*`. While the server is running, interactive docs with full request and response schemas are at **http://localhost:8000/docs**.

## Conventions

- **Auth:** every endpoint except `/api/health`, `/api/meta`, `/api/holdings/template` and `/api/auth/{login, signup, logout, forgot, reset}` requires the `pd_session` cookie. Missing or invalid sessions return `401`. Admin-only endpoints return `403` for other users.
- **Errors** have the form `{"detail": "message"}`. Validation errors (`422`) carry a list in `detail`.
- **`502`** means an upstream data source (usually Yahoo Finance) failed. **`503`** means a feature isn't configured (missing API key or library).
- **Numbers:** `NaN` and infinities are returned as `null`.
- **Periods** are one of `1mo`, `3mo`, `6mo`, `1y`, `2y`, `5y`.
- **Currencies** are one of USD, SGD, EUR, GBP, JPY, CAD, AUD, HKD, CNY, INR, KRW, THB, MYR, IDR, PHP, VND.
- **Symbols** match `[A-Za-z0-9.\-^=]{1,20}` and are normalized through `config.TICKER_ALIASES`.

## Auth

| Method | Path | Body | Returns |
|---|---|---|---|
| POST | `/api/auth/login` | `{username, password}` | `{username, role}` and sets the cookie |
| POST | `/api/auth/signup` | `{username, password}` | Creates a `user` account and signs in. The username may contain letters, digits, `-` and `_`; the password must be 10–128 characters, must not contain the username and must not be a common password. `403` when `ALLOW_SIGNUP=0` |
| POST | `/api/auth/logout` | none | Clears the cookie |
| GET | `/api/auth/me` | none | `{username, role, email, gemini_private, private_terms}` |
| POST | `/api/auth/password` | `{current_password, new_password}` | `{ok}`. Signs out other sessions and re-issues this one's cookie |
| PUT | `/api/auth/email` | `{email \| null, current_password}` | `{email}`. Links, changes or (with `null`) removes your email |
| PUT | `/api/auth/private-terms` | `{terms: string[]}` (up to 100) | `{private_terms}`. Words always hidden from Gemini; blanks, duplicates and single characters are dropped |
| PUT | `/api/auth/gemini-privacy` | `{private}` | `{gemini_private}`. Whether Gemini is kept from your portfolio; see [Configuration → Google Gemini](CONFIGURATION.md) |
| POST | `/api/auth/forgot` | `{identifier}` (username or email) | Always `{ok: true, email_enabled}`, whether or not the account exists. Sends or logs a reset link; one per account per minute |
| GET | `/api/auth/reset?token=…` | none | `{username}` if the link is valid, otherwise `400` with the reason (expired, used, invalid) |
| POST | `/api/auth/reset` | `{token, new_password}` | `{username}`. Sets the password and signs out all sessions |

## Settings and metadata

| Method | Path | Notes |
|---|---|---|
| GET | `/api/meta` | `{currencies, periods}` |
| GET | `/api/settings` | `{base_currency, last_updated}`. Shared by all users |
| PUT | `/api/settings` | `{base_currency}` |
| GET | `/api/features` | `{ml, gemini, sentiment: {libraries, api_key, enabled, scorer: {finance, model, note}}, chronos: {available, model, note}}`: which optional features are available |

## Holdings

| Method | Path | Notes |
|---|---|---|
| GET | `/api/holdings` | `{holdings: [{index, Symbol, Quantity, Purchase_Price, Purchase_Date, Currency}], last_updated}` |
| POST | `/api/holdings` | `{symbol, quantity > 0, purchase_price > 0, purchase_date: "YYYY-MM-DD", currency}` → `201` |
| DELETE | `/api/holdings/{index}` | Deletes one lot by its position in the list |
| DELETE | `/api/holdings` | Deletes all lots |
| POST | `/api/holdings/import` | `multipart/form-data` with field `file` (CSV). Appends rows → `{imported}` |
| GET | `/api/holdings/export` | CSV download of your lots |
| GET | `/api/holdings/template` | Example CSV |
| POST | `/api/holdings/backup` | Writes `data/backups/portfolio_backup_<user>_<timestamp>.json` (holdings, sales, plan and settings) → `{file}` |
| POST | `/api/holdings/sell` | `{symbol, quantity > 0, price > 0, sale_date, fees ≥ 0}` → `201` with the sale record. Takes shares from the oldest lots bought on or before the sale date (FIFO); the price and fees are in the lots' currency. `400` if fewer shares were held then, or the date is in the future |
| GET | `/api/transactions` | `{transactions: [{id, type: "SELL", Symbol, Quantity, Price, Fees, Date, Currency, lots[], cost, proceeds, realized, created}]}`, newest first. `lots` are the lot pieces the sale used |
| DELETE | `/api/transactions/{id}` | Undoes a sale: its shares go back into the lots they came from |

CSV columns: `Symbol, Quantity, Purchase_Price, Purchase_Date[, Currency]`. Currency defaults to USD.

## Portfolio analytics

**`GET /api/portfolio/metrics?base=USD`** returns:

```jsonc
{
  "base_currency": "USD",
  "holdings_count": 18,          // lots, including any that couldn't be priced
  "total_invested": 28209.75,    // in base currency
  "total_value": 90921.01,
  "total_gain": 62711.26,
  "total_gain_pct": 222.3,
  "rows": [                      // one per priced lot
    { "index": 0, "symbol": "AMD", "quantity": 42, "currency": "USD",
      "purchase_price": 110.78, "purchase_date": "2025-04-04", "current_price": 615.73,
      "invested": 4652.76, "value": 25860.66, "gain": 21207.9,          // lot currency
      "invested_base": 4652.76, "value_base": 25860.66, "gain_base": 21207.9,
      "gain_pct": 455.8, "weight": 28.4 }
  ],
  "unpriced": []                 // symbols excluded because no price was available
}
```

**`GET /api/portfolio/performance?base=USD&period=1y`** returns:

- `series`: daily rows `{date, "Portfolio", "S&P 500", <symbol>...}`, each rebased to 100 at the start of the period. `Portfolio` holds today's weights constant over the period.
- `series_keys`: the column names in `series`.
- `risk`: `[{symbol, volatility, avg_daily_return}]`, in percent, from trailing 1-year daily returns.
- `sectors`: `[{sector, value}]`.
- `summary`: totals, `best` and `worst` by return.
- `unpriced`: as for metrics.

**`GET /api/portfolio/returns?base=USD`** rebuilds what your money actually did from every purchase (lots held plus lots since sold), every sale and the dividends paid on shares you held. `{empty: true}` without holdings; otherwise:

- `start` (first purchase), `years`
- `summary`: `bought`, `sold` (proceeds), `value` (at live quotes), `dividends` (gross), `dividends_ttm`, `realized`, `unrealized` (against each lot's cost at the purchase day's exchange rate), `total_gain` (value + sold + dividends − bought), `twr_pct` and `twr_annual_pct` (time-weighted; Modified Dietz days), `irr_pct` (money-weighted, a year), `benchmark_twr_pct`, `benchmark_irr_pct` and `benchmark_value` (the same purchases and sales made in SPY, dividends reinvested), `value_added` (value + dividends − benchmark value)
- `series`: weekly `{date, value, with_income, net_invested, benchmark_value, twr, benchmark_twr}`
- `dividends`: `by_symbol[]`, `by_year[]`, `recent[]` (`symbol, date, per_share, shares, amount, currency`)
- `realized[]`: each sale with `proceeds`, `cost`, `gain`, `gain_pct` (lot currency), `gain_base` (at the purchase and sale days' exchange rates) and `held_days`
- `missing`: symbols without price history

**`GET /api/portfolio/risk?base=USD`** uses daily dividend-adjusted returns converted to the base currency: the last 252 trading days for statistics, 3 years for the drawdown, 10 years for stress tests.

- `portfolio`: `vol`, `beta`, `var95`, `var99`, `cvar95` (1-day, percent) with `var95_amount` and `cvar95_amount`, `diversification_ratio`, `effective_bets` (its square), `hhi_bets` (1 / Σw²), `avg_corr` (weighted pairwise), `bench_vol`, `max_drawdown` with `drawdown_from` and `drawdown_to`, `current_drawdown`, `bench_max_drawdown`, `holdings_used`
- `holdings[]`: `symbol, name, value, weight, sector, industry, country, fund, currency, vol, beta, risk_share` (% of portfolio variance), `corr_to_rest`, `history_days`
- `correlation`: `{symbols, matrix}`
- `exposure`: `sector[]` (funds looked through to their sector weights, each with the S&P 500's `benchmark` weight), `industry[]`, `currency[]`, `country[]`, each `{name, weight}`
- `scenarios[]`: `{name, start, end, benchmark, portfolio, loss, estimated, rows[{symbol, return, estimated}]}`; a holding not trading then is its beta × the S&P 500's move
- `drawdown[]`: `{date, portfolio, benchmark}` in percent below the peak
- `flags[]`: `{severity, kind, message}` for positions above 20%, industries above 30%, sectors above twice their S&P 500 weight, fewer than 4 effective bets, and beta above 1.3
- `excluded`: holdings with under 60 days of history

**`POST /api/portfolio/whatif?base=USD`** with `{trades: [{symbol, amount}]}` (1–10; `amount` in the base currency, positive to buy, negative to sell) returns `{trades, symbols, before, after}`, where each side is the risk `portfolio` block plus `total_value`, `flags`, `top_industry`, `holdings` (by symbol) and `worst_scenario`.

**`GET /api/market/context`** returns the market backdrop: `{as_of, regime ("risk-on", "mixed" or "risk-off"), supportive, headwinds, readings[{key, label, value, unit, detail, lean ("supportive", "neutral" or "headwind"), rule}], sectors[{symbol, name, return_3m, return_12m, vs_spy_3m}], spy_3m, spy_12m}`. Cached for 30 minutes.

## Plan

| Method | Path | Notes |
|---|---|---|
| GET | `/api/plan` | `{targets: {symbol: weight %}, band, watchlist[], journal: {symbol: {thesis, sell_if[], review_date, created, updated}}, alerts[{id, symbol, kind, value, note, created}]}` |
| GET | `/api/plan/status?base=USD` | Everything checked against today's prices: `triggered[{kind ("rule", "earnings", "review" or "drift"), symbol, message, severity, rule}]`, `rebalance[{symbol, weight, target, value, drift, trade, shares, price, currency}]`, `calendar[{symbol, date, days, held, watching}]`, `watchlist[]` (quote, `last_call`, `held`, `thesis`), `holdings[]` (position, `quote`, `thesis`, `last_call`, `alerts`), `alerts[]`, `kinds`, `band`, `targeted`, `review_soon[]` |
| PUT | `/api/plan/targets` | `{targets: {symbol: 0–100}, band?}`. `400` if they add up to more than 100 |
| POST | `/api/plan/watchlist` | `{symbol}` → `201` |
| DELETE | `/api/plan/watchlist/{symbol}` | |
| PUT | `/api/plan/journal/{symbol}` | `{thesis, sell_if: [string], review_date: "YYYY-MM-DD" \| null}` |
| DELETE | `/api/plan/journal/{symbol}` | |
| POST | `/api/plan/alerts` | `{symbol, kind, value, note?}` → `201`. `kind` is `price_above`, `price_below` (value is a price), `below_cost`, `weight_above`, `drawdown` (below the 52-week high) or `estimate_cut` (this year's EPS estimate over 90 days), all in percent |
| DELETE | `/api/plan/alerts/{id}` | |

## Research

| Method | Path | Body / query | Returns |
|---|---|---|---|
| GET | `/api/stocks/{symbol}/technical` | `period, rsi_period (5–30), macd_fast (5–20), macd_slow (≤50, > fast), bb_period (10–30), bb_std (1–3)` | `{quote: {price, date, change, change_pct, volume}, signals, series}`. `signals` has `rsi, macd, bollinger, trend` (`sma20/50/200`, `golden_cross`), `obv, adx` (`value, plus_di, minus_di, state, direction`), `atr` (`value, pct`), `momentum` (`return_12_1`) and `high_52w` (`value, distance`). `series` rows hold `close, volume, rsi, macd, signal, hist, bb_upper/middle/lower, sma20, sma50, sma200, ema20, obv, obv_ema, adx, plus_di, minus_di, atr_pct` |
| GET | `/api/stocks/{symbol}/technical/backtest` | the same indicator parameters, no `period` (always 5 years) | `{symbol, start, end, horizons: [5, 20, 60], cooldown_days, min_events, signals: [{id, indicator, label, expect "up"\|"down", count, last, horizons: [{days, n, hit_rate, avg_return, baseline_hit, baseline_avg, verdict}]}]}`. `verdict` is `worked`, `failed`, `no_edge` or `insufficient` |
| GET | `/api/stocks/{symbol}/technical.csv` | `period` | OHLCV plus every indicator, as CSV |
| GET | `/api/stocks/{symbol}/fundamentals` | none | `{profile, as_of, headline, ratios: {Valuation, Profitability, Liquidity, Leverage, Growth}, analyst, history, quality, risk, earnings, statements: {income, balance, cashflow}}`. Each ratio has a `unit`: `x` (multiple), `fraction` (0.25 = 25%) or `percent` (150 = 1.5×), and may carry a `note` (for example "n/m: loss-making"). `profile.kind` is `financial`, `reit` or `general`. `history.rows[]` give each measure by fiscal year with `now`, `median`, `vs_median` and `verdict`. `quality` holds `piotroski` (`score`, `tested`, `state`, `tests[]`) and `metrics[]`; `risk.metrics[]`; `earnings` holds `surprises[]`, `beats`, `estimates[]` and `next_date` |
| POST | `/api/stocks/{symbol}/predict` | `{period "1y"\|"2y"\|"5y", rf_estimators 50–300, rf_depth 2–12, test_size 20–40, use_chronos}` | `{last_close, last_date, samples, baseline, models: [{name, kind, metrics: {rmse_pct, mae_pct, skill, dm_p, directional_accuracy, direction_ci, verdict}, next_return, next_close}], best_model, any_skill, alpha, range: {sigma_pct, next, coverage, backtest}, series, feature_importance, chronos}` |
| GET | `/api/stocks/{symbol}/valuation` | none | `{symbol, peers: {source ("finnhub" or "portfolio"), industry, peers[{symbol, name, market_cap, <metric keys>}], rows[{key, label, unit, better, value, median, n, rank, vs_median}]}, anchor: {currency, discount_rate, discount_inputs{risk_free, beta, premium, clamped}, terminal_growth, fcf, enterprise_value, implied_growth, sensitivity[{rate, growth}], history{revenue_cagr, fcf_cagr, eps_growth_next_year, years}, yields{earnings, forward_earnings, fcf, dividend, shareholder, treasury_10y}, yield_gap, note}}`. `rank` is the share of peers the company is cheaper than (multiples) or better than (margins, growth, ROE). Percent values are in percent |
| GET | `/api/sentiment/account` | none | SERPapi quota: `{plan, searches_left, used_this_month, …}` (uses no search) |
| POST | `/api/stocks/{symbol}/sentiment` | `{days 7\|30, source "both"\|"finance"\|"news"}` | `{overall, index, ci, n, counts, pct, excluded, scorer, query, price, price_move_share, daily, articles[{title, source, published, status, sentiment, score, confidence, price_move, …}], errors, searches_used}`. `overall` is Positive/Negative only when the 95% CI excludes zero, Neutral otherwise, null under 5 headlines. **Uses 1–2 SERPapi searches** |

## AI assessment

The assessment runs in two steps, so you can review the inputs before spending a Gemini call.

1. **`POST /api/stocks/{symbol}/assessment`** with `{period, include_sentiment}` gathers technicals, fundamentals, the forecast models' skill summary and GARCH range (always on 2 years), optional sentiment (2 SERPapi searches) and your position. It returns the **context**: `{technical, fundamental, predictive, sentiment, sentiment_status, position, scores, ai_available, …}`.
2. **`POST /api/stocks/{symbol}/assessment/ai`** takes that context object as the body. It calls Gemini (`gemini-3.5-flash-lite`) with a JSON response schema, logs token usage, appends the result to your recommendation history, and returns:

   ```jsonc
   { "recommendation": "BUY" | "HOLD" | "SELL", "confidence": 1-10,
     "time_horizon": "Short-term" | "Medium-term" | "Long-term", "price_target": 650.0 | null,
     "steps": [{ "title": "...", "content": "..." }], "strengths": [...], "risks": [...],
     "position_advice": "...", "summary": "...", "model": "gemini-3.5-flash-lite", "generated_at": "..." }
   ```

3. **`POST /api/stocks/{symbol}/assessment/evaluate`** with `{context, ai}` (the step-2 result) picks skills by rule, computes their facts, and asks Gemini to review the recommendation. It never changes the recommendation, and confidence can only go down. The result is attached to the matching history record when `ai.generated_at` matches one (`saved`):

   ```jsonc
   { "verdict": "stands" | "weakened" | "contradicted", "confidence_adjusted": 1-10, "original_confidence": 7,
     "recommendation": "BUY", "summary": "...",
     "findings": [{ "skill": "valuation-sanity", "stance": "supports" | "challenges" | "neutral",
                    "severity": "info" | "minor" | "major", "finding": "..." }],
     "counter_case": "...", "invalidation": ["..."],
     "entry_plan": { "approach": "all_at_once" | "staged" | "wait", "detail": "...", "size": "...", "review_when": "..." } | null,
     "skills": [{ "name", "title", "description", "applies_when", "evidence", "rationale", "sources": [{ "cite", "url" }] }],
     "checks": [{ "skill", "check", "passed": true, "detail": "..." }],
     "model": "gemini-3.5-flash-lite", "generated_at": "...", "saved": true }
   ```

**`POST /api/reports/assessment.pdf`** takes `{context, ai, evaluation?}` and returns a PDF download.

## Chat

| Method | Path | Notes |
|---|---|---|
| GET | `/api/chat/providers` | `{default: "local", local: {model, problem}, gemini: {model, problem}}`. `problem` is `null` when that model can answer, otherwise why not |
| POST | `/api/chat` | `{provider: "local" \| "gemini", messages: [{role: "user" \| "assistant", content}], page: {path, title, symbol, text}}`. Streams NDJSON, one event per line: `{"type": "redacted", "items": [{label, count, text}]}` first when personal details were hidden from Gemini, `{"type": "tool", "name", "args"}` when an analysis runs, `{"type": "text", "text"}` for answer text, then `{"type": "done", "model"}` or `{"type": "error", "message"}` |

## Track record and usage

| Method | Path | Notes |
|---|---|---|
| GET | `/api/scheduled` | Scheduled runs (any signed-in user; only their own runs are listed): `installed`, `next_run`, `next_compare` (the next run is a comparison week), `model`, `chunk` (stocks per hourly start, for the run in progress or the next one), `held` (your holdings, assessed first in the next run), `list_size` (the fixed list), `total` (stocks in the next run), `hours` (first and last), `local_problem` (why Ollama can't run, or null), `status` (the current or last run: `run`, `user`, `total`, `held`, `done`, `current`, `ok`, `failed`, `providers`, `started`, `finished`, `state` of `running` (a chunk is going), `waiting` (with `next_chunk`), `finished` or `incomplete`) and `runs[]` (your last 10, newest first: `run`, `started`, `finished`, `providers`, `skipped`, `total` stocks, `held` (how many were your holdings), `ok` and `failed` counts, and up to 5 `errors`) |
| POST | `/api/scheduled/run` | **Admin.** Starts the next chunk of today's run in a background process, starting the run if there isn't one → `{started: true}`. `409` if a chunk is running |
| GET | `/api/track-record?horizon=21` | `horizon` is the checkpoint to score at, in trading days (`5`, `21`, `63`, `126`, `252`), or `stated` for each call's own horizon. Returns `{signals, symbols, horizon, flat_band, benchmark_available, calibration, confidence, ranking, rules, models}`. Returns are total returns: the stock's dividend-adjusted closes against SPY's. Each signal is a history record plus `current_price`; `entry_date` and `entry_price` (first split-adjusted close after the call); `return_pct`, `benchmark_pct` and `excess_pct` since entry; `split_factor` (shares today per share held at the call); `momentum` (12-1 month, at entry); `model`, `provider` (`gemini` or `local`), `source` (`manual` or `scheduled`), `run`, `held` (you held the stock at the call; null for scheduled calls from before this was saved), `in_list` (on the scheduled fixed list; null for manual calls), `prompt_version`, `quote_date` and `expected_excess` (the call's expected return vs the S&P 500 in points, prompt version 3 on); `rules` (what each simple rule would have said: `always_buy`, `momentum`, `analyst`, `app_score`); `checkpoints[]` (`days`, `label`, `date`, `stock`, `benchmark`, `excess`, null until reached); `target` (`price`, `hit`, `date`); `path` (BUYs: `[date, stock growth of 1, S&P 500 growth of 1]` per day); `score_days`, `score_excess` (stock − S&P 500 there), `score_return` and `outcome` (`Correct`, `Wrong`, `Flat`, `Neutral` or `Pending`). `calibration` has `groups[]` (`verdict`, `n`, `win_rate`, `avg_return` for scored BUY/SELL calls by evaluation verdict, including `not_evaluated`), `evaluated`, `lowered`, `brier_original` and `brier_adjusted`. `rules` has `checked` (calls past the checkpoint) and `rows[]` (`key`, `label`, `calls`, `win_rate`, `avg_return`) for the AI and each rule. `models` has `models[]`, `all[]` and `paired[]` (`model`, `calls`, `win_rate`, `avg_return`), `pairs`, `pairs_checked` and `agreement` (% of paired calls where both models made the same call). `confidence` has `rows[]` (`label` of the confidence bucket, `n`, `stated` and `actual` hit rate in percent, Wilson `ci`), `n` and `brier`. `ranking` scores each scheduled run (per model, at least `min_ranked` scored calls): `runs[]` (`run`, `model`, `n`, `ic` (Spearman), `spread` (calls above the run's median strength minus those below), `top`, `bottom`), `count`, `mean_ic`, `ic_t`, `mean_spread`, `positive_share` |
| GET | `/api/usage?days=30` | Totals, `daily[]`, `operations[]`, `symbols[]`, `rate {rpm, tpm, rpd, limits, resets_at}` (Gemini requests and tokens in the last minute, requests since midnight Pacific; `resets_at` is the next reset in local time), `recent[]` (last 25) |
| GET | `/api/usage/export?days=30` | CSV |
| DELETE | `/api/usage/old?days=90` | **Admin.** Deletes older records → `{removed}` |

## Retrograde

| Method | Path | Notes |
|---|---|---|
| GET | `/api/retrograde?start_year=2026&end_year=2027` | Years default to last year through next year (1950–2100, at most 5 years). `refresh=true` skips the cache. Returns `range`, `generated_at`, `reference` (the source shadows come from), `agree_hours`, `planets[]` (`id`, `name`), `sources[]` (`id` of `horizons`, `swisseph` or `local`, `name`, `method`, `url`, `status` `ok` or `error`, `error`, `stations`) and `periods[]` touching the range: `planet`, `name`, `start` and `end` (consensus UTC times), `shadow_start`, `shadow_end`, `station_retrograde` and `station_direct` (`sign`, `degree`, `longitude`, `time`, `by_source` times, `spread_hours`, `agree`) and `verification` (`status` of `verified`, `partial`, `conflict` or `single`, `sources_agreeing`, `sources_available`, `max_spread_hours`). `502` if no source answers. Cached in `data/retrograde_<start>_<end>.json` for 30 days, or an hour if a source failed |
| GET | `/api/retrograde/etfs` | The preset ETF list (`symbol`, `name`, `group`) and the `benchmark` (SPY) |
| GET | `/api/retrograde/markets?planets=mercury,venus,mars&symbols=SMH,VNQ&since=2000&window=retrograde` | Event study of ETF returns inside vs outside retrograde windows. `symbols` defaults to the preset list (up to 25; SPY is always added), `since` is 2000 to two years ago, `window` is `retrograde` or `shadow`. Returns `tests[]` (`id` of each planet, plus `any` and `overlap` when more than one is chosen; `share_of_days`), `results[]` per symbol (`name`, `group`, `first_date`, `tests[id].absolute` and `.excess` vs SPY: `days_in`, `days_out`, `ann_in`, `ann_out`, `diff`, `daily_diff_bp`, `vol_in`, `vol_out`, `up_in`, `up_out`, circular-shift `p`, Benjamini–Hochberg `q`, `shifts`), `periods[]` (each window's `returns[symbol]`: `ret` and `typical` same-length return), weekly `growth[]` and `missing` symbols. Cached in memory for an hour |

## Data and users

| Method | Path | Notes |
|---|---|---|
| GET | `/api/data/stats` | Your lot, symbol and currency counts, plus the files in `data/`. Non-admins see only their own files and `settings.json` |
| GET | `/api/data/raw` | Your raw `portfolio_<user>.json` |
| PUT | `/api/data/raw` | Replaces it. Must contain `holdings[]`, each with `Symbol, Quantity, Purchase_Price, Purchase_Date` |
| GET | `/api/users` | **Admin.** `[{username, role, email, created_at, last_login}]` |
| POST | `/api/users` | **Admin.** `{username, password, role: "user"\|"admin", email?}` |
| GET | `/api/health` | `{ok: true}` |
