# Portfolio Dashboard

A personal portfolio tracker and stock research app. Track holdings across 16 currencies, compare performance against the S&P 500, analyze stocks with technical, fundamental, machine-learning and news-sentiment tools, and get AI-assisted BUY/HOLD/SELL assessments from Google Gemini or a local model (Ollama). A track record scores past AI calls against the S&P 500 at fixed checkpoints after each call, and a chat assistant on every page answers questions about what you're looking at.

The interface follows Apple's Human Interface Guidelines: translucent materials, spring-based motion, SF Pro typography and semantic colors that adapt to light and dark mode.

**Stack:** Next.js 16 (App Router, React 19, Tailwind CSS v4, Motion, Recharts) for the web app and FastAPI (Python) for the API. Data is stored as local JSON files, so there is no database to run.

## Quick start

You need Python 3.10 or later and Node.js 20.9 or later.

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

The chat assistant and scheduled assessments can also run on a free local model through [Ollama](https://ollama.com): install it and run `ollama pull qwen3.5:9b`. No key is needed.

See [Configuration](documentations/CONFIGURATION.md) for every setting, including session security for deployment.

## Features

| Page | What it does |
|---|---|
| **Overview** | Portfolio value, all-time gain, allocation, gain by position and a positions table, all in your base currency |
| **Holdings** | Add, delete, import and export purchase lots (CSV), and create backups |
| **Performance** | Your current allocation vs the S&P 500 over 1M–5Y, sector mix and per-holding volatility |
| **Technicals** | Price with Bollinger Bands or 20/50/200-day averages, RSI, MACD, OBV, ADX and ATR with adjustable periods, 12-1 momentum and 52-week high, and a 5-year back-test of how each signal has worked on the stock |
| **Fundamentals** | Company profile, ratios read against the company's own history, earnings quality (Piotroski F-score, accruals), financial risk (Altman Z″, interest cover, net debt), earnings surprises and estimate revisions, analyst targets and up to 5 years of financial statements |
| **Forecast** | Ridge, gradient boosting and random forest models (plus optional pretrained Chronos-Bolt) for the next session's return, tested walk-forward against a no-change forecast, and a GARCH range for the next close |
| **Sentiment** | Recent firm-specific headlines from Google Finance and Google News, scored by a financial-news language model, with a confidence interval on the net tone and research sources |
| **AI Assessment** | Combines all of the above, plus your position, into a Gemini recommendation with step-by-step reasoning and a PDF report |
| **Track Record** | Every past AI recommendation scored against the S&P 500 at 1 week to 1 year, compared with simple rules and between Gemini and a local model, plus price targets, a "follow every BUY" simulation against the index, and the status of the twice-weekly scheduled runs |
| **Retrograde** | A calendar and timeline of Mercury, Venus, Mars (and optionally outer-planet) retrogrades, their shadows and overlaps, with every date cross-checked across NASA JPL Horizons, Swiss Ephemeris and a local ephemeris, plus astrological readings with sources and a statistical test of whether sector ETFs (semiconductors, data centres, REITs and more) behave differently during retrogrades than the S&P 500 |
| **API Usage** | Gemini and local-model calls, tokens, estimated cost and Gemini rate-limit headroom |
| **Settings** | Account, password, appearance, base currency, raw data editor and (for admins) user management |
| **Chat** | The button at the bottom right of every page: ask about the page you're on, and the assistant looks up technicals, fundamentals, forecasts, news, your portfolio or past assessments as needed. Runs on the local model or Gemini |

[Features](documentations/FEATURES.md) explains how each figure is calculated and what its limits are.

## Project structure

```
backend/                FastAPI server
  main.py               app entry point (uvicorn backend.main:app)
  routes/               HTTP endpoints: auth, portfolio, analysis, chat, admin
  auth.py               users, emails, password reset tokens, signed session cookies
  ratelimit.py          in-memory limits on sign-in, sign-up and reset attempts
  mailer.py             password-reset email (SMTP, or console fallback)
  manage.py             CLI: list users, set email, print a reset link
  storage.py            JSON persistence in data/
  market.py             quotes, history, company info, FX (Finnhub + Yahoo with circuit breaker)
  portfolio.py          valuation, performance vs benchmark, risk, sectors
  technical.py          indicator series, signals and the 5-year signal back-test
  fundamentals.py       ratios, statements, analyst view
  fundamental_history.py  ratios at each past fiscal year-end
  quality.py            Piotroski F-score, accruals, Altman Z″, coverage, earnings record
  predictive.py         next-session return models, walk-forward tested against no change
  volatility.py         GARCH(1,1) range for the next close
  sentiment.py          SERPapi news, filtering, financial-news model scoring
  assessment.py         signal aggregation and structured assessment (Gemini or Ollama)
  batch.py              scheduled assessments over a fixed list of 30 stocks
  chat.py               page-aware chat with the analyses as tools (Ollama or Gemini)
  evaluation.py         second-look review of an assessment with research-based skills
  evaluation_benchmark.py  planted-error benchmark of the evaluation (live Gemini calls)
  skills/               the evaluation's skills (SKILL.md files)
  reports.py            PDF export
  track_record.py       hindsight scoring of past recommendations
  usage.py              AI usage log (Gemini and local model) and summaries
config.py               shared settings: API keys, ticker aliases, currencies, periods
technical_indicators.py RSI, MACD, Bollinger, moving averages, OBV, ML features
web/                    Next.js web app
  src/app/(app)/        signed-in pages
  src/app/(auth)/       sign in, sign up, forgot and reset password
  src/components/       UI primitives, charts, app shell and chat panel
  src/lib/              API client, formatting, motion presets, theme, types, method & evidence text
  src/proxy.ts          redirects signed-out visitors to /login
tests/                  pytest suite (PYTHONPATH=. pytest tests)
data/                   your data (git-ignored)
documentations/         guides
dev.sh                  starts both servers
schedule.sh             installs the scheduled assessments as a launchd job (macOS)
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
./schedule.sh install                   # twice-weekly assessments on a local model (needs Ollama)
```

The API serves interactive docs at http://localhost:8000/docs while it's running.

## Troubleshooting

- **"Prices unavailable for …"**: Yahoo Finance is rate-limiting. After a failure the app skips Yahoo for 5 minutes and uses Finnhub for US-listed symbols, so add `FINN_API_KEY`. Foreign listings (for example `005930.KS`) depend on Yahoo alone.
- **Forgot your password**: choose **Forgot password?** on the sign-in page. Without email set up, the reset link appears in the terminal running `./dev.sh`. You can also run `python3 -m backend.manage reset-link <username>`. See [Password reset](documentations/CONFIGURATION.md#password-reset).
- **Signed out unexpectedly**: sessions last 7 days, and changing or resetting a password signs out other devices. If `data/.session_secret` changes (or `SESSION_SECRET` does), existing sessions become invalid.
- **AI Assessment button disabled**: `GEMINI_API_KEY` is missing or still the placeholder. Restart the API after editing `.env`.
- **Chat says Ollama isn't running**: open the Ollama app and pull the model (`ollama pull qwen3.5:9b`), or switch the chat to Gemini in its header.
- **Requests time out after 30 seconds**: the web app's proxy allows 180 seconds (`web/next.config.ts`). If you run the API behind another proxy, raise its timeout too.
- **Port already in use**: stop the old process, or pick other ports: `API_PORT=8001 WEB_PORT=3001 ./dev.sh`. The script passes ports explicitly, so a `PORT` variable in your shell is ignored.

## Disclaimer

Market data may be delayed. Model and AI outputs are statistical estimates, not financial advice.

## License

Personal/educational use. Add your preferred license here if distributing.
