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

`backend/predictive.py`, `backend/volatility.py`. Sources for every choice are in the page's **Method & evidence** panel (`web/src/lib/forecast-evidence.ts`).

- **Target:** the next session's **return**, not its price. Prices trend, so models trained on price levels look accurate while mostly echoing today's close, and tree models can't predict outside their training range.
- **Inputs (13, all scale-free):** 1, 5 and 20-day returns; distance from the 20 and 50-day averages; RSI; MACD histogram ÷ price; Bollinger %B; 20-day volatility and the 5/20-day volatility ratio; the day's high–low range; the overnight gap; and log volume against its 20-day average.
- **Models:**
  - **Ridge regression:** linear, with shrinkage chosen by cross-validation.
  - **Gradient boosting:** shallow trees (depth 3), slow learning rate.
  - **Random forest:** trees and depth set on the page; each leaf holds at least 20 days.
  - **Chronos-Bolt (optional):** Amazon's pretrained time-series transformer, run zero-shot. Off by default; needs `chronos-forecasting` (see `requirements.txt`). The tiny model (~35 MB) downloads on first use and needs ~750 MB of memory while running.
- **Testing:** walk-forward. The last *test window* % of days (default 30%) is forecast in monthly blocks, each by a model refitted on everything before it.
- **Benchmark:** a no-change forecast (return of zero). Every model is scored against it:
  - **Skill** is the out-of-sample R² of Campbell & Thompson (2008): the share of the no-change forecast's squared error removed.
  - **p-value** is a one-sided Diebold–Mariano test with the Harvey–Leybourne–Newbold correction. A model is labelled *Beats no change* only below 0.05 ÷ number of models (Bonferroni), and *Worse than no change* when significantly worse.
  - **Direction right** comes with a Wilson 95% interval, and is shown next to the share of up days, which an always-up guess would score.
- **Next-session range:** GARCH(1,1) with Student-t errors, fitted by maximum likelihood in `volatility.py` (numpy/scipy only; matches the `arch` package). The backtest fits on data before the test window and checks how often the 80% and 95% ranges held the next close, with a Kupiec coverage test.

**What to expect.** On daily data, models rarely beat no change by a significant margin. In testing on AAPL, NVDA, KO, TSM, JPM, D05.SI, SPY and RIVN, none did after the Bonferroni correction, and Chronos-Bolt's point forecasts were worse than no change on every stock checked. The GARCH ranges were well calibrated, with 74–80% of closes inside the 80% range and 93–96% inside the 95% range.

## Sentiment

`backend/sentiment.py`. Requires `SERP_API_KEY` and the SERPapi and NLTK packages. The financial-news model also needs `torch` and `transformers`; without them, headlines are scored with VADER. Run `python3 setup_sentiment.py` to check.

- **Sources** (each costs one SERPapi search):
  - **Google Finance** news for `TICKER:EXCHANGE`. Yahoo's exchange codes are mapped to Google's (`NMS → NASDAQ`, `NYQ → NYSE`, `SES → SGX` …); exchanges not on the list skip this source.
  - **Google News** for "*company name* stock", with the name cleaned of suffixes such as Inc. or Holdings. ETFs search "*TICKER* ETF" and indices their name.
- **Which headlines count.** Every headline is shown, but only these are scored:
  - published within the window (7 or 30 days). Google News ranks by relevance and returns stories months old
  - not a duplicate: a headline sharing 70% or more of its words with one already counted is left out, keeping the newest
  - not a routine filing: automatically generated fund-holdings posts ("Stock Sold by XYZ Advisors LLC") and pre-planned insider sales (Form 4, 10b5-1)
  - firm-specific: it names the company, a common alternative name (Google for GOOGL, TSMC for TSM) or the ticker. Funds and indices skip this check.
- **Scoring.** Each headline is read by `mrm8488/distilroberta-finetuned-financial-news-sentiment-analysis` (82M parameters, about 330 MB, downloaded on first use; change with `SENTIMENT_MODEL`). Its score is P(positive) − P(negative), from −1 to +1, and its label is the most likely class. With VADER, the score is the compound score and ±0.05 sets the label.
- **Net tone** is the mean score of the scored headlines with a 95% t-interval. It is **Positive** or **Negative** only when the interval excludes zero, otherwise **no clear tilt**; under 5 headlines is too few to judge.
- **Context:** the price change over the same window, and the share of headlines that report a price move ("slides 3%", "is up today"), since those restate moves already made.
- **Tone by day** charts each day's mean score. **Check Quota** calls SERPapi's account endpoint, which uses no searches.
- **Method & evidence** cites the research behind each step, as on Technicals, Fundamentals and Forecast.

**Why this model.** Scorers were compared on 2,388 human-labelled financial-news headlines that none of the models were trained on (the Twitter Financial News validation set):

| Scorer | Accuracy | Macro-F1 | Positive read as negative, or vice versa |
|---|---|---|---|
| DistilRoBERTa, financial news | 76% | 0.71 | 8% |
| FinBERT-tone (Huang, Wang & Yang 2023) | 74% | 0.68 | 7% |
| FinBERT (Araci 2019) | 72% | 0.66 | 11% |
| Loughran–McDonald word list | 60% | 0.46 | 18% |
| VADER | 50% | 0.45 | 24% |
| TextBlob (previously shown) | 49% | 0.38 | 30% |

Calling every headline neutral scores 66% accuracy, because most headlines are. DistilRoBERTa was the most accurate and needs about half FinBERT's compute; it scores 100 headlines in under a second on the CPU.

**What to expect.** News tone describes coverage; research finds it predicts returns only weakly and briefly, so it is context rather than a forecast. In live runs on AAPL, KO and DBS, none showed a clear tilt: the 95% intervals were about ±0.2 wide on 33–57 headlines.

**Known limits.** The model misreads about 1 headline in 4, often valuation language. Name matching can let in related companies that share the name (Coca-Cola HBC, Coca-Cola Europacific) or a headline where the company is the source ("…upgraded by DBS Bank"). Feeds of automated price reports (common for Singapore stocks) push up the share of price-move headlines.

## AI Assessment

`backend/assessment.py`

**Step 1: Run Analysis** gathers these in parallel:

- Technical signals, using default periods
- Fundamentals
- The forecast models on 2 years of history, whatever lookback is chosen, so they have enough data
- News sentiment (optional, last 7 days, both sources, up to 2 searches)
- Your position in the symbol: total shares, average cost, value and unrealized return across all lots

The **Signal profile** radar turns these into 0–100 scores. A missing input scores a neutral 50, and every score is clamped to 0–100.

| Axis | Formula |
|---|---|
| Valuation | 100 − (P/E − 15) × 2 |
| Growth | (revenue growth % + 20) × 2.5 |
| Profitability | ROE % × 4 |
| Momentum | 100 − \|RSI − 50\| × 2 (rewards a non-extreme RSI) |
| Balance sheet | 100 − (Debt/Equity ×) × 40 |
| Sentiment | 50 unless the net tone's 95% interval excludes zero; then 50 + net tone × 50 |
| Forecast | 50 unless a model significantly beats no change; then 50 + (its predicted return ÷ GARCH daily volatility) × 50 |

These are rough heuristics for visual comparison. Gemini doesn't see them.

**Step 2: Generate Assessment** sends Gemini (`gemini-3.5-flash-lite`) a compact prompt:

- Technical readings
- Key ratios, with margins and growth correctly as percentages
- The analyst consensus and target
- Each forecast model's skill against no change, its significance and direction accuracy, and the GARCH range. When no model beats no change, the prompt says to treat the forecasts as no signal
- Net tone with its interval and verdict, the price change over the window, the share of headlines reporting price moves, a note that tone is context rather than a forecast, and the 5 strongest-toned headlines
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
