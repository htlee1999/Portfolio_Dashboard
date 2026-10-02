# Portfolio Dashboard

A personal portfolio tracker and stock research app. Track holdings across 16 currencies, compare performance against the S&P 500, analyze stocks with technical, fundamental, machine-learning and news-sentiment tools, and get AI-assisted BUY/HOLD/SELL assessments from Google Gemini. A track record scores past AI calls against today's price.

The interface follows Apple's Human Interface Guidelines: translucent materials, spring-based motion, SF Pro typography and semantic colors that adapt to light and dark mode.

**Stack:** Next.js 16 (App Router, React 19, Tailwind CSS v4, Motion, Recharts) for the web app and FastAPI (Python) for the API. Data is stored as local JSON files, so there is no database to run.

## Quick start

You need Python 3.9 or later and Node.js 20.9 or later.

```bash
git clone <repo-url> portfolio && cd portfolio
pip install -r requirements.txt
cp config.env.example .env      # then add your API keys (see below)
./dev.sh                        # starts the API on :8000 and the web app on :3000
```

Open http://localhost:3000. On a fresh install, the API creates an **admin** account and prints its generated password in the terminal (or set `ADMIN_PASSWORD` in `.env` beforehand). Change it in **Settings → Change Password**.

To run the two servers separately:

```bash
python3 -m uvicorn backend.main:app --reload --port 8000   # from the repo root
cd web && npm install && npm run dev                       # http://localhost:3000
```

### API keys

All keys are optional. The core portfolio features work without any of them.

| Variable | Enables | Get one |
|---|---|---|
| `FINN_API_KEY` | Faster, more reliable live quotes for US-listed symbols. Yahoo Finance is used otherwise. | [finnhub.io](https://finnhub.io/) (free) |
| `GEMINI_API_KEY` | AI Assessment | [aistudio.google.com](https://aistudio.google.com/) (free tier) |
| `SERP_API_KEY` | Sentiment, and the news input to AI Assessment | [serpapi.com](https://serpapi.com/) (free monthly searches) |
| `SMTP_*` | Emailing password-reset links. Without it, links appear in the API terminal | any SMTP provider, such as a Gmail app password |

See [Configuration](documentations/CONFIGURATION.md) for every setting, including session security for deployment.

## Features

| Page | What it does |
|---|---|
| **Overview** | Portfolio value, all-time gain, allocation, gain by position and a positions table, all in your base currency |
| **Holdings** | Add, delete, import and export purchase lots (CSV), and create backups |
| **Performance** | Your current allocation vs the S&P 500 over 1M–5Y, sector mix and per-holding volatility |
| **Technicals** | Price with Bollinger Bands or moving averages, RSI, MACD and OBV, with adjustable periods |
| **Fundamentals** | Company profile, valuation and profitability ratios, analyst targets and 4–5 years of financial statements |
| **Forecast** | Ridge, gradient boosting and random forest models (plus optional pretrained Chronos-Bolt) for the next session's return, tested walk-forward against a no-change forecast, and a GARCH range for the next close |
| **Sentiment** | Recent firm-specific headlines from Google Finance and Google News, scored by a financial-news language model, with a confidence interval on the net tone and research sources |
| **AI Assessment** | Combines all of the above, plus your position, into a Gemini recommendation with step-by-step reasoning and a PDF report |
| **Track Record** | Every past AI recommendation scored against today's price, plus a "follow every BUY" simulation |
| **API Usage** | Gemini calls, tokens, estimated cost and rate-limit headroom |
| **Settings** | Account, password, appearance, base currency, raw data editor and (for admins) user management |

[Features](documentations/FEATURES.md) explains how each figure is calculated and what its limits are.

## Project structure

```
backend/                FastAPI server
  main.py               app entry point (uvicorn backend.main:app)
  routes/               HTTP endpoints: auth, portfolio, analysis, admin
  auth.py               users, emails, password reset tokens, signed session cookies
  mailer.py             password-reset email (SMTP, or console fallback)
  manage.py             CLI: list users, set email, print a reset link
  storage.py            JSON persistence in data/
  market.py             quotes, history, company info, FX (Finnhub + Yahoo with circuit breaker)
  portfolio.py          valuation, performance vs benchmark, risk, sectors
  technical.py          indicator series and signals
  fundamentals.py       ratios, statements, analyst view
  predictive.py         next-session return models, walk-forward tested against no change
  volatility.py         GARCH(1,1) range for the next close
  sentiment.py          SERPapi news, filtering, financial-news model scoring
  assessment.py         signal aggregation and Gemini structured assessment
  reports.py            PDF export
  track_record.py       hindsight scoring of past recommendations
  usage.py              Gemini usage log and summaries
config.py               shared settings: API keys, ticker aliases, currencies, periods
technical_indicators.py RSI, MACD, Bollinger, moving averages, OBV, ML features
web/                    Next.js web app
  src/app/(app)/        signed-in pages
  src/app/(auth)/       sign in and sign up
  src/components/       UI primitives, charts and app shell
  src/lib/              API client, formatting, motion presets, theme, types
  src/proxy.ts          redirects signed-out visitors to /login
data/                   your data (git-ignored)
documentations/         guides
dev.sh                  starts both servers
setup_sentiment.py      checks the sentiment dependencies and SERPapi key
```

## Documentation

- [Architecture](documentations/ARCHITECTURE.md): how the pieces fit, request flow, caching and auth
- [API reference](documentations/API.md): every endpoint
- [Features](documentations/FEATURES.md): calculations, models and limitations
- [Design system](documentations/DESIGN_SYSTEM.md): tokens, typography, motion, components and chart rules
- [Configuration](documentations/CONFIGURATION.md): environment variables, accounts and deployment
- [Data](documentations/DATA.md): files in `data/` and their formats

## Common tasks

```bash
cd web && npm run build && npm start    # production build of the web app
cd web && npx eslint src && npx tsc --noEmit   # lint and type-check
python3 setup_sentiment.py              # verify sentiment setup
```

The API serves interactive docs at http://localhost:8000/docs while it's running.

## Troubleshooting

- **"Prices unavailable for …"**: Yahoo Finance is rate-limiting. After a failure the app skips Yahoo for 5 minutes and uses Finnhub for US-listed symbols, so add `FINN_API_KEY`. Foreign listings (for example `005930.KS`) depend on Yahoo alone.
- **Forgot your password**: choose **Forgot password?** on the sign-in page. Without email set up, the reset link appears in the terminal running `./dev.sh`. You can also run `python3 -m backend.manage reset-link <username>`. See [Password reset](documentations/CONFIGURATION.md#password-reset).
- **Signed out unexpectedly**: sessions last 7 days, and changing or resetting a password signs out other devices. If `data/.session_secret` changes (or `SESSION_SECRET` does), existing sessions become invalid.
- **AI Assessment button disabled**: `GEMINI_API_KEY` is missing or still the placeholder. Restart the API after editing `.env`.
- **Requests time out after 30 seconds**: the web app's proxy allows 180 seconds (`web/next.config.ts`). If you run the API behind another proxy, raise its timeout too.
- **Port already in use**: stop the old process, or pick other ports: `API_PORT=8001 WEB_PORT=3001 ./dev.sh`. The script passes ports explicitly, so a `PORT` variable in your shell is ignored.

## Disclaimer

Market data may be delayed. Model and AI outputs are statistical estimates, not financial advice.

## License

Personal/educational use. Add your preferred license here if distributing.
