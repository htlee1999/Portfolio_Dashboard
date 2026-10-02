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
| POST | `/api/auth/signup` | `{username, password}` | Creates a `user` account and signs in. The username may contain letters, digits, `-` and `_`; the password needs at least 6 characters |
| POST | `/api/auth/logout` | none | Clears the cookie |
| GET | `/api/auth/me` | none | `{username, role, email}` |
| POST | `/api/auth/password` | `{current_password, new_password}` | `{ok}`. Signs out other sessions and re-issues this one's cookie |
| PUT | `/api/auth/email` | `{email \| null, current_password}` | `{email}`. Links, changes or (with `null`) removes your email |
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
| POST | `/api/holdings/backup` | Writes `data/backups/portfolio_backup_<user>_<timestamp>.json` → `{file}` |

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

## Research

| Method | Path | Body / query | Returns |
|---|---|---|---|
| GET | `/api/stocks/{symbol}/technical` | `period, rsi_period (5–30), macd_fast (5–20), macd_slow (≤50, > fast), bb_period (10–30), bb_std (1–3)` | `{quote, signals, series}`. `series` rows hold `close, volume, rsi, macd, signal, hist, bb_upper/middle/lower, sma20, sma50, ema20, obv, obv_ema` |
| GET | `/api/stocks/{symbol}/technical.csv` | `period` | OHLCV plus every indicator, as CSV |
| GET | `/api/stocks/{symbol}/fundamentals` | none | `{profile, headline, ratios: {Valuation, Profitability, Liquidity, Leverage, Growth}, analyst, statements: {income, balance, cashflow}}`. Each ratio has a `unit`: `x` (multiple), `fraction` (0.25 = 25%) or `percent` (150 = 1.5×) |
| POST | `/api/stocks/{symbol}/predict` | `{period "1y"\|"2y"\|"5y", rf_estimators 50–300, rf_depth 2–12, test_size 20–40, use_chronos}` | `{last_close, last_date, samples, baseline, models: [{name, kind, metrics: {rmse_pct, mae_pct, skill, dm_p, directional_accuracy, direction_ci, verdict}, next_return, next_close}], best_model, any_skill, alpha, range: {sigma_pct, next, coverage, backtest}, series, feature_importance, chronos}` |
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

**`POST /api/reports/assessment.pdf`** takes `{context, ai}` and returns a PDF download.

## Track record and usage

| Method | Path | Notes |
|---|---|---|
| GET | `/api/track-record` | `{signals, symbols}`. Each signal is a history record plus `current_price`, `return_pct` and `outcome` (`Correct`, `Wrong`, `Neutral` or `Pending`) |
| GET | `/api/usage?days=30` | Totals, `daily[]`, `operations[]`, `symbols[]`, `rate {minute, hour, day_tokens, limits}` (requests in the last minute and hour; tokens today), `recent[]` (last 25) |
| GET | `/api/usage/export?days=30` | CSV |
| DELETE | `/api/usage/old?days=90` | **Admin.** Deletes older records → `{removed}` |

## Data and users

| Method | Path | Notes |
|---|---|---|
| GET | `/api/data/stats` | Your lot, symbol and currency counts, plus the files in `data/`. Non-admins see only their own files and `settings.json` |
| GET | `/api/data/raw` | Your raw `portfolio_<user>.json` |
| PUT | `/api/data/raw` | Replaces it. Must contain `holdings[]`, each with `Symbol, Quantity, Purchase_Price, Purchase_Date` |
| GET | `/api/users` | **Admin.** `[{username, role, email, created_at, last_login}]` |
| POST | `/api/users` | **Admin.** `{username, password, role: "user"\|"admin", email?}` |
| GET | `/api/health` | `{ok: true}` |
