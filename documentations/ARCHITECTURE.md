# Architecture

Portfolio Dashboard has two processes: a **Next.js web app** that renders the interface, and a **FastAPI server** that does all data fetching, analysis and persistence. They talk over a JSON HTTP API. Data lives in JSON files under `data/`.

```
 Browser ──► Next.js (:3000) ──/api/* rewrite──► FastAPI (:8000) ──► Finnhub / Yahoo Finance
   ▲            │                                     │          ──► SERPapi (news)
   │            └─ src/proxy.ts: no session cookie    │          ──► Google Gemini
   │               → redirect to /login               │          ──► Ollama (local model)
   │                                                  ▼
   └──────── pd_session cookie (signed) ──────── data/*.json
```

## Request flow

1. The browser loads a page from Next.js. Every page is a client component, prerendered as a static shell.
2. `src/proxy.ts` runs first. If there is no `pd_session` cookie, it redirects to `/login?next=…`. This check is *optimistic*: it only looks for the cookie's presence.
3. The page fetches data with `useApi()` (SWR) from `/api/...`. `next.config.ts` rewrites `/api/:path*` to the FastAPI server, so the browser only ever talks to one origin and the session cookie stays first-party.
4. FastAPI verifies the cookie's signature on every request (`auth.current_user`). A 401 makes the client redirect to `/login`.
5. Route handlers call the service modules, which return plain dicts. `utils.clean()` converts numpy/pandas values to JSON-safe types (NaN becomes `null`) before the response is sent.

Handlers are synchronous (`def`, not `async def`), so FastAPI runs them in its thread pool. Slow network calls (yfinance, Gemini) therefore don't block other requests.

## Backend (`backend/`)

The backend is a Python package run from the repository root as `uvicorn backend.main:app`. That lets it import the shared root modules `config.py` (API keys, ticker aliases, currencies, periods, feature flags) and `technical_indicators.py` (indicator math).

| Module | Responsibility |
|---|---|
| `main.py` | Loads `.env`, creates the app and mounts the routers |
| `routes/auth.py` | Sign in, sign up, sign out, current user, change password |
| `routes/portfolio.py` | Settings, holdings CRUD, CSV import/export, backups, metrics, performance |
| `routes/analysis.py` | Technicals and the signal back-test, fundamentals, predictions, sentiment, assessment, evaluation, PDF, scheduled runs, track record |
| `routes/chat.py` | Chat providers and the streaming chat endpoint |
| `routes/admin.py` | Usage stats, data files, raw JSON editor, user management |
| `auth.py` | User store (`data/users.json`), password hashing, linked emails, reset tokens, session cookies, `current_user` / `admin_user` dependencies |
| `mailer.py` | Sends password-reset emails over SMTP, falling back to the console |
| `manage.py` | Command-line account recovery: list users, set email, print a reset link, test email |
| `ratelimit.py` | In-memory sliding windows for failed password checks, sign-ups and reset requests |
| `storage.py` | All file I/O. Writes are atomic (temp file + rename). |
| `market.py` | Quotes, OHLCV history, company info, statements and FX rates, with caching and the Yahoo circuit breaker |
| `portfolio.py` | Valuation in a base currency, rebased performance series, risk and sector breakdowns |
| `technical.py` | Indicator series, the current signal state, and a 5-year back-test of each signal on the stock |
| `fundamentals.py` | Ratio groups, statements, analyst targets; converts market cap to the reporting currency for valuation ratios |
| `fundamental_history.py` | Ratios at each past fiscal year-end, and where today's trailing figure sits against their median |
| `quality.py` | Piotroski F-score, accruals, asset growth, share-count change, Altman Z″, interest coverage, net debt/EBITDA, earnings surprises and estimate revisions |
| `predictive.py` | Next-session return models (ridge, gradient boosting, random forest, optional Chronos-Bolt), walk-forward tested against a no-change forecast |
| `volatility.py` | GARCH(1,1) with Student-t errors for the next-session range |
| `sentiment.py` | SERPapi news fetch, headline filtering (window, duplicates, routine filings, firm-specific), financial-news model scoring with VADER fallback |
| `assessment.py` | Gathers every signal in parallel, scores the radar, calls Gemini or the local model (Ollama) with a response schema and records the result and its inputs |
| `batch.py` | Scheduled assessments over a fixed stock list: local model on Mondays and Fridays, plus Gemini on the same context in the last week of the month |
| `chat.py` | Page-aware chat: the page's text goes in the system prompt, and the analyses are offered as tools; streams NDJSON from Ollama or Gemini |
| `evaluation.py` | Second look at an assessment: picks skills by rule, computes their facts and rule screens, one Gemini review, enforces that it can only flag and lower confidence |
| `skills/*/SKILL.md` | The evaluation's skills: instructions, when each applies, evidence rating and sources (Agent Skills format) |
| `reports.py` | Renders an assessment as a PDF (reportlab) |
| `track_record.py` | Scores past recommendations against the S&P 500 at fixed checkpoints, and compares them with simple rules and between models |
| `evaluation_benchmark.py` | On-demand benchmark of the evaluation with planted errors (live Gemini calls) |
| `usage.py` | Appends to and summarizes `data/gemini_usage.json` (Gemini and local-model calls) |
| `utils.py` | `clean()`, `num()`, `ttl_cache`, `series_points()` |

### Market data and caching

- **Quotes** (`market.price`): Finnhub first when `FINN_API_KEY` is set and the symbol is US-listed, falling back to Yahoo's last 5-day close.
- **History, info and statements** come from Yahoo Finance (yfinance).
- **Circuit breaker:** after any Yahoo failure, Yahoo is skipped for 5 minutes, so a rate limit doesn't make every request wait for a network timeout. A success closes it again.
- **`ttl_cache`** caches results in memory per arguments, and caches only non-`None` results, so a transient failure is retried on the next request:

  | Data | TTL |
  |---|---|
  | Quotes and history | 10 min |
  | Info, statements, FX | 1 hour |

- Portfolio valuation fetches prices for all symbols concurrently (8 threads).
- **Ticker normalization:** `config.normalize_symbol` maps aliases (for example `TSMC → TSM`, `BRK.B → BRK-B`) so the same company is never stored under two symbols.

Caches are per process. Restarting the API clears them.

### Authentication

- **Passwords:** stored in `data/users.json` as PBKDF2-SHA256 (`pbkdf2_sha256$iterations$salt$hash`). Legacy salted SHA-256 hashes from the original app are verified and upgraded on the next sign-in.
- **Rate limits:** `backend/ratelimit.py` keeps in-memory sliding windows for failed password checks, sign-ups and reset requests; see [Configuration](CONFIGURATION.md#security-notes).
- **CSRF:** a middleware in `backend/main.py` rejects state-changing requests without `X-Requested-With`, which `web/src/lib/api.ts` adds to every call.
- **Sessions:** a stateless cookie, `pd_session`, signed with itsdangerous (`URLSafeTimedSerializer`). It is `HttpOnly`, `SameSite=Lax`, lasts 7 days, and is `Secure` when the request came over HTTPS (or per `COOKIE_SECURE`).
- **Signing key:** `SESSION_SECRET`, or a random key generated once into `data/.session_secret` (mode 600).
- **Accounts must still exist:** each request re-reads the user, so deleting an account signs it out immediately.
- **Session versions:** the cookie carries the account's `session_version`, which a password change or reset increments, signing out every other session.
- **Password reset** (`auth.make_reset_token` / `reset_password`): a signed token (salt `pd-password-reset`, 30-minute expiry) holding the username and an HMAC fingerprint of the current password hash, so each link works once with nothing stored. `mailer.py` delivers it by SMTP, or prints it to the API console when SMTP isn't configured. `backend/manage.py` offers the same from the command line.
- **Roles:** `admin` adds user management, deleting old usage records, and visibility of every file in `data/`.

## Web app (`web/`)

```
src/
  app/
    layout.tsx           html shell, theme boot script, providers
    providers.tsx        MotionConfig (honors Reduce Motion), theme, toasts
    globals.css          design tokens, type scale, materials (see DESIGN_SYSTEM.md)
    (auth)/              /login, /signup, /forgot, /reset (shared AuthShell)
    (app)/layout.tsx     SessionProvider + AppShell; renders nothing until /auth/me resolves
    (app)/<page>/page.tsx one folder per screen
  components/
    shell/               AppShell (sidebar, tab bar, toolbar, scheduled-run indicator), nav, PageHeader,
                         ResearchPage (symbol in the URL, research tabs), SymbolPicker, CurrencyMenu, Chat
    ui/                  Button, Card/List/ListRow/Badge, Segmented, TextField, Select, Switch, Slider,
                         Sheet, Disclosure, Banner, Spinner, Skeleton, EmptyState, Stat, Delta, AnimatedNumber, Toast,
                         EvidenceTag/EvidenceGuide (method & evidence panels)
    charts/charts.tsx    TimeSeries, SignedBars, HBars, Donut, ScoreRadar, Legend
  lib/
    api.ts               fetch wrapper, download(), useApi() (SWR)
    session.tsx          current user, base currency, logout
    theme.tsx            system / light / dark preference
    storage.ts           SSR-safe localStorage hook
    format.ts            money, percent, compact, dates
    motion.ts            spring presets
    portfolio.ts         currencies, lot → position aggregation
    media.ts             media-query hook for phone layouts
    scheduled.ts         scheduled-run status polling
    evidence.ts, *-evidence.ts  evidence ratings, research summaries and sources for the Method & evidence panels
    types.ts             response types mirroring the API
  proxy.ts               optimistic auth redirect
```

**State**

- **Server data** lives in SWR's cache, keyed by API path. Mutations call `mutate()` on affected keys; for example, adding a holding revalidates every `/holdings`, `/portfolio/` and `/data/` key.
- **Base currency** is server-side (`/settings`). Changing it revalidates all `/portfolio/*` queries.
- **The research symbol** lives in the URL (`?symbol=NVDA`), so research pages are linkable. The last one used is remembered in `localStorage`.
- **Theme preference** is stored in `localStorage`. An inline script sets `data-theme` before first paint, so there's no flash of the wrong appearance.
- **Results from on-demand operations** are page state and aren't cached: forecast training, sentiment, assessment. These cost time or API credits, so they only run when you press the button.
- **Chat** keeps its conversation in component state (cleared on reload or **New chat**); the chosen provider is stored in `localStorage`. Each request sends the visible text of `main#main`, so the assistant sees what the page shows.

**Next.js 16 notes**

- Middleware is now called **Proxy** (`src/proxy.ts`).
- Pages that read `useSearchParams` are wrapped in `<Suspense>` (`ResearchPage`).
- External rewrites time out after 30s by default, so `experimental.proxyTimeout` is raised to 180s for Gemini and model training.
- Chat replies stream through the same rewrite as `application/x-ndjson`; the API sets `X-Accel-Buffering: no` so a proxy in between doesn't hold the stream back.

## Concurrency and limits

- The JSON store suits a single small server. Writes are atomic per file, but there is no cross-process locking: run one API process.
- Holding deletion is by list index. The client refetches after each change, so indexes stay in sync for a single user.
- The AI and evaluation steps (`…/assessment/ai`, `…/assessment/evaluate`) trust the context the client sends back from step 1, instead of recomputing it. That avoids spending SERPapi credits twice, and is fine because users only write to their own history.
