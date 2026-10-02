# Features

What each screen shows, how its numbers are calculated, and where the limits are. Code references point to the module that does the work.

- [Overview](#overview)
- [Holdings](#holdings)
- [Performance](#performance)
- [Technicals](#technicals)
- [Fundamentals](#fundamentals)
- [Forecast](#forecast)
- [Sentiment](#sentiment)
- [AI Assessment](#ai-assessment)
- [Track Record](#track-record)
- [API Usage](#api-usage)
- [Settings](#settings)

---

## Overview

`backend/portfolio.py → metrics()`

- **Pricing:** each lot is priced at the latest quote (see [Architecture → Market data](ARCHITECTURE.md#market-data-and-caching)).
- **Lot values:** cost basis = shares × purchase price; value = shares × current price. Both are in the lot's currency.
- **Base currency:** both values are converted at the current FX rate. The rate comes from Yahoo `XXXYYY=X`, then exchangerate-api.com, and finally 1:1 if both fail.
- **Totals and weights:** totals are summed in the base currency. Weight = position value ÷ total value.
- **Positions:** lots of the same symbol are combined into one position (`web/src/lib/portfolio.ts`). Average cost = total cost ÷ total shares.
- **Return %:** calculated in the lot's own currency, so currency moves don't distort a stock's return. **Gain** in the base currency does include currency effects.
- **Unpriced symbols** are excluded from the totals and listed in a warning banner.
- **Allocation donut:** shows the 7 largest positions; the rest are grouped as "Other".

## Holdings

Each row is one purchase **lot** (symbol, shares, price, date, currency).

- **Adding:** symbols are normalized on entry. For example `TSMC → TSM`, `Alibaba → BABA`, `BRK.B → BRK-B` (`config.TICKER_ALIASES`).
- **CSV import** appends rows. The columns are `Symbol, Quantity, Purchase_Price, Purchase_Date, Currency`, and Currency is optional (default USD). Download the template from the empty state or the actions row.
- **Export** downloads your lots as CSV. **Backup** writes a JSON snapshot to `data/backups/`. **Delete All** asks for confirmation first.

## Performance

`backend/portfolio.py → performance()`

- **Growth of 100:** each symbol's close is rebased to 100 on the first day of the period.
  - **Portfolio** is the value-weighted average of those series, using *today's* weights for the whole period. It is a backtest of your current allocation, not your actual historical returns: it ignores when you bought and any trades.
  - The **S&P 500** (`^GSPC`) is the benchmark.
  - You can add up to 6 holdings to compare. Each keeps its color while pinned.
- **Relative** = portfolio return − benchmark return over the period.
- **Sectors** come from Yahoo's company profile. ETFs show as "ETF / Fund".
- **Risk:**
  - Volatility = standard deviation of daily returns × √252, over the trailing 12 months, whatever period is selected.
  - Average daily return is the mean of daily returns over the same window.

## Technicals

`technical_indicators.py → TechnicalAnalysis`, `backend/technical.py`

| Indicator | Calculation | Signal shown |
|---|---|---|
| RSI (default 14) | 100 − 100 / (1 + RS), where RS is the exponentially smoothed average gain ÷ average loss | > 70 overbought, < 30 oversold, otherwise neutral |
| MACD (12, 26, 9) | EMA(fast) − EMA(slow); signal line = EMA(9) of MACD; histogram = MACD − signal | MACD above signal = bullish, otherwise bearish |
| Bollinger Bands (20, 2σ) | SMA(20) ± k × rolling standard deviation; %B = (price − lower) ÷ (upper − lower) | %B > 1 above upper band, < 0 below lower band, otherwise within |
| Moving averages | SMA 20, SMA 50 (EMA 20 is in the export) | Price above both = uptrend, below both = downtrend, otherwise mixed |
| OBV | Cumulative volume, added on up days and subtracted on down days; EMA(10) overlay | OBV above its EMA = rising |

- **Indicator settings:** the sliders change the periods, and the charts refetch after you stop dragging (350 ms debounce). The MACD signal period is fixed at 9.
- **Export Indicator Data** downloads OHLCV plus every indicator as CSV.
- **Signal cards** reflect the current settings. If you change the RSI period, the RSI card uses the new period too.

## Fundamentals

`backend/fundamentals.py`. All data comes from Yahoo Finance via yfinance.

- **Ratio groups:**
  - Valuation: P/E, Forward P/E, PEG, P/B, P/S, EV/Revenue, EV/EBITDA
  - Profitability: ROE, ROA, gross, operating and profit margins
  - Liquidity: current and quick ratios
  - Leverage: Debt/Equity, Beta
  - Growth: revenue and earnings growth
- **Units:** margins and growth arrive as fractions and are displayed as percentages. Yahoo reports Debt/Equity as a percentage (150 = 1.5×), and the app displays it as a multiple. Dividend yield is already a percentage.
- **Analyst view:** consensus key and score (1 = strong buy … 5 = sell), mean, low and high targets, and upside to the mean target. The range bar marks the current price and the mean.
- **Statements:** up to 5 fiscal years of selected rows from the income statement, balance sheet and cash flow, shown in compact notation.

## Forecast

`backend/predictive.py`, `technical_indicators.py → PredictiveAnalysis`

- **Target:** the next session's close.
- **Features (20):**
  - SMA 5/20 and EMA 12/26
  - Bollinger upper, middle and lower bands and %B
  - High/low and open/close ratios
  - RSI, plus MACD with its signal and histogram
  - 20-day volume average and volume ratio
  - 1, 5 and 20-day price changes
  - 20-day volatility
- **Split:** chronological. The last *test size* % of days (default 20%) is held out, so models are only tested on dates after their training window.
- **Models:**
  - **Random Forest:** the average of a Random Forest and a single Decision Tree (same depth).
  - **SVM:** RBF-kernel support vector regression on standardized features.
- **Metrics on the test window:**
  - RMSE and MAE are in price units.
  - **Directional accuracy** is how often the predicted day-over-day move had the right sign (50% is a coin flip).
- **Best model** is the one with the lowest RMSE.
- **Next-session estimate:** each model applied to the most recent day's features.

**Limitations.** Tree models can't predict outside the price range they were trained on, so after a strong rally or sell-off they lag badly. The page shows a caution banner when any estimate is more than 8% from the last close. A single dominant feature (often SMA 5) means the model is mostly echoing recent price. Treat these as statistical estimates only.

## Sentiment

`backend/sentiment.py`. Requires `SERP_API_KEY` and the NLTK, TextBlob and SERPapi packages. Run `python3 setup_sentiment.py` to check.

- **Sources:**
  - Google Finance news for `SYMBOL:EXCHANGE`, with the exchange taken from Yahoo
  - Google News for "SYMBOL stock"
  - Or both. Each source costs one SERPapi search.
- Articles are de-duplicated by title. Each title plus snippet is scored by:
  - **VADER** compound score from −1 to +1: ≥ 0.05 is positive, ≤ −0.05 negative, otherwise neutral
  - **TextBlob** polarity (−1 to +1) and subjectivity (0 = factual, 1 = opinion)
- **Overall** is the label of the *average* VADER compound score. The gauge shows that average on the −1…+1 scale, and the bar shows the positive, neutral and negative split.
- **Check Quota** calls SERPapi's account endpoint, which uses no searches.

Automated scoring misses sarcasm and context. Read the articles.

## AI Assessment

`backend/assessment.py`

**Step 1: Run Analysis** gathers these in parallel:

- Technical signals, using default periods
- Fundamentals
- A Random Forest forecast with default parameters
- News sentiment (optional, 15 articles per source, 2 searches)
- Your position in the symbol: total shares, average cost, value and unrealized return across all lots

The **Signal profile** radar turns these into 0–100 scores. A missing input scores a neutral 50, and every score is clamped to 0–100.

| Axis | Formula |
|---|---|
| Valuation | 100 − (P/E − 15) × 2 |
| Growth | (revenue growth % + 20) × 2.5 |
| Profitability | ROE % × 4 |
| Momentum | 100 − \|RSI − 50\| × 2 (rewards a non-extreme RSI) |
| Balance sheet | 100 − (Debt/Equity ×) × 40 |
| Sentiment | (average VADER + 1) × 50 |
| Model accuracy | directional accuracy × 100 |

These are rough heuristics for visual comparison. Gemini doesn't see them.

**Step 2: Generate Assessment** sends Gemini (`gemini-2.5-flash`) a compact prompt:

- Technical readings
- Key ratios, with margins and growth correctly as percentages
- The analyst consensus and target
- The ML forecast and its backtest accuracy
- Sentiment and up to 5 headlines
- Your position

Gemini must return JSON that matches a schema: recommendation (BUY, HOLD or SELL), confidence (1–10), time horizon, price target, step-by-step reasoning, strengths, risks, advice on the position, and a summary. Because the output is structured, nothing is guessed from free text.

Each assessment is:

- appended to `data/recommendation_history_<user>.json`, where it feeds the Track Record
- logged to `data/gemini_usage.json`, with real token counts from the API response
- exportable as a PDF (summary table, position advice, reasoning, strengths and risks)

AI output can be wrong and is not financial advice.

## Track Record

`backend/track_record.py`

Every saved recommendation is scored against the **current** price.

| Signal | Return shown | Outcome |
|---|---|---|
| BUY | price change since the signal | Correct if the price rose |
| SELL | −(price change): the loss avoided | Correct if the price fell |
| HOLD | price change | Neutral (not scored) |

If there is no current price, the outcome is **Pending**.

- **Win rate** = correct ÷ (correct + wrong). HOLDs are excluded.
- **Average, best and worst** use the returns shown above.
- **"What if you followed every BUY?"** assumes $1,000 was invested at each BUY signal and values every position at today's price. The chart shows the cumulative return in signal order.
- Each signal expands to show prices, the target, your position when it was generated, the reasoning and the strengths and risks. Records saved by the original Streamlit version have no separate steps and show their original reasoning text instead.

Scoring ignores the stated time horizon: a long-term BUY from last week is judged on one week of movement.

## API Usage

`backend/usage.py`

- Every Gemini call is logged, failures included. Each record holds the timestamp, model, operation, symbol, input and output tokens, estimated cost and any error.
- **Token counts** come from Gemini's `usage_metadata`. Older records (and failed calls) use an estimate of about 4 characters per token.
- **Cost** is estimated from `PRICING` (USD per 1K input and output tokens). Update it when Google changes prices.
- **Rate-limit meters** show requests in the last minute and hour, and tokens used today, against `RATE_LIMITS` (Gemini free-tier defaults). Adjust them to your plan.
- Export the selected range as CSV. Admins can delete records older than 90 days.

## Settings

- **Account:** link an email (used for password resets), change password, sign out. Forgotten passwords are reset from **Forgot password?** on the sign-in page; see [Configuration → Password reset](CONFIGURATION.md#password-reset).
- **Appearance:** Automatic (follows the OS), Light or Dark. This is stored per browser.
- **Base currency:** the currency for totals and charts. It's stored in `data/settings.json` and shared by all users.
- **Data:** lot, symbol and currency counts, and the list of files in `data/`. **Edit portfolio JSON** lets you edit your holdings file directly; it is validated before saving.
- **Users (admins only):** list accounts and create users or admins.
- On phones, Settings also links to Performance, Track Record and API Usage, which aren't in the tab bar.
