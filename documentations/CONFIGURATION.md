# Configuration

## Environment variables

The API reads `.env` from the repository root at startup (`python-dotenv`). Copy `config.env.example` to `.env` and fill in what you need, then **restart the API** after any change.

| Variable | Default | Purpose |
|---|---|---|
| `FINN_API_KEY` | none | Finnhub real-time quotes for US-listed symbols, and the industry peer lists on Fundamentals. Without it, every quote comes from Yahoo Finance, which rate-limits aggressively, and peers fall back to the stocks you hold or watch |
| `GEMINI_API_KEY` | none | Enables AI Assessment |
| `GEMINI_RPM`, `GEMINI_TPM`, `GEMINI_RPD` | `15`, `250000`, `500` | Gemini's limits: requests per minute, tokens per minute, requests per day (free tier for `gemini-3.5-flash-lite`). Raise them on a paid tier |
| `SERP_API_KEY` | none | Enables Sentiment and the news input to AI Assessment |
| `SENTIMENT_MODEL` | `mrm8488/distilroberta-finetuned-financial-news-sentiment-analysis` | Hugging Face model that scores headlines. Any model whose labels are positive, neutral and negative works. Needs `torch` and `transformers` |
| `OLLAMA_URL` | `http://localhost:11434` | Local Ollama server for scheduled assessments and chat |
| `OLLAMA_MODEL` | `qwen3.5:9b` | Local model for scheduled assessments and chat (where it's the default). Pull it first: `ollama pull qwen3.5:9b` (7.6 GB; about 7 GB of memory while running) |
| `OLLAMA_THINK` | `0` | `1` lets the local model think before answering in scheduled assessments. On an M2 that took 6–7 minutes a stock instead of about 1. Chat never thinks |
| `CHRONOS_MODEL` | `amazon/chronos-bolt-tiny` | Pretrained forecaster for the optional Chronos-Bolt model on Forecast |
| `SESSION_SECRET` | auto-generated | Key that signs session cookies, at least 32 characters. If unset, a random key is created in `data/.session_secret` on first run. **Required** on Vercel (or with `REQUIRE_SESSION_SECRET=1`) |
| `COOKIE_SECURE` | auto | Cookies are `Secure` whenever the request arrived over HTTPS. Set `1` to force on, `0` to force off |
| `ADMIN_PASSWORD` | generated | Password for the `admin` account created on a fresh install. If unset, a random one is printed to the API console |
| `ALLOW_SIGNUP` | `1` | Set to `0` to close public sign-up; admins can still create accounts in **Settings → Users** |
| `TRUST_PROXY` | off | Set to `1` only when the API sits behind a proxy that sets `X-Forwarded-For`, so rate limits apply per real client IP |
| `API_DOCS` | on (off on Vercel) | Serves interactive API docs at `/docs` |
| `SMTP_HOST`, `SMTP_PORT` (587), `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM` | none | Email delivery for password resets and the Plan alert digest sent when a scheduled run starts. Port 465 uses SSL; anything else uses STARTTLS |
| `APP_URL` | `http://localhost:3000` | Public address of the web app, used to build reset links |

The **web app** reads one variable, from the shell or from `web/.env.local` (Next.js doesn't read the root `.env`):

| Variable | Default | Purpose |
|---|---|---|
| `API_URL` | `http://127.0.0.1:8000` | Where `/api/*` requests are proxied |

Placeholder values from `config.env.example` (such as `your_gemini_api_key_here`) are treated as "not configured".

## Getting API keys

**Finnhub** (recommended)
1. Sign up at [finnhub.io](https://finnhub.io/) and copy the API key from the dashboard.
2. Add `FINN_API_KEY=…` to `.env`.

The free tier covers real-time quotes for US-listed symbols. Foreign listings (`.KS`, `.TW`, `.AS` …) still use Yahoo. Where possible, aliases map companies to their US ADRs (for example `TSMC → TSM`).

**Google Gemini**
1. Go to [aistudio.google.com](https://aistudio.google.com/), sign in, and choose **Get API key → Create API key**.
2. Add `GEMINI_API_KEY=…` to `.env`.

The model is `gemini-3.5-flash-lite` (`backend/assessment.py → MODEL`), also used by the evaluation and by chat when you pick Gemini. An assessment's prompt is about 4,000 tokens, plus the response. The cost estimates on API Usage are set in `backend/usage.py` (`PRICING`); update them if Google changes its pricing.

**Rate limits.** The free tier has three limits, shared by every key in the same Google Cloud project: 15 requests a minute, 250,000 tokens a minute and 500 requests a day for `gemini-3.5-flash-lite`. The daily count resets at midnight Pacific time. Google no longer publishes the numbers in its docs; check yours at [aistudio.google.com/rate-limit](https://aistudio.google.com/rate-limit) and set `GEMINI_RPM`, `GEMINI_TPM` and `GEMINI_RPD` if they differ. Every Gemini request (assessment, evaluation, each round of a chat answer, scheduled runs) checks them first: when the minute is full it waits up to about a minute for room, and when the day's requests are used up it's refused with the reset time instead of failing at Google. The counts come from `data/gemini_usage.json`, so calls made with the same key outside this app aren't seen. An assessment or evaluation is one request; a chat answer is one per tool round, up to 5.

**Privacy.** On the free tier, Google may use prompts and responses to improve its models, and human reviewers may read them (detached from your account first); its terms ask you not to send personal or confidential information. On a paid tier (billing enabled on the key's Cloud project) it doesn't train on them. So **Settings → AI Privacy** (on by default, per user, stored as `gemini_private` in `data/users.json`) keeps your own data away from Gemini (`backend/privacy.py`):

- Assessments and evaluations on Gemini leave out the *Current position* and *Portfolio fit* sections: share count, average cost, unrealized gain, portfolio weight, risk share and your largest holdings. The call is about the stock either way; the position advice becomes general. Your history and saved inputs still keep the full context.
- Evaluations also withhold the assessment's position advice, which a local-model call may have written with your figures.
- Gemini chat isn't offered the portfolio, risk, actual returns, plan or past-assessments tools, and sees a page's text only on Technicals, Fundamentals, Forecast, Sentiment and Retrograde.

Prices, financials and headlines still go to Gemini; they're public. The local model always gets everything, since it never leaves the machine.

**Redaction.** Whatever that setting, text bound for Gemini first goes through `backend/redact.py`, which swaps personal details for placeholders such as `[email-1]` and swaps the originals back into the reply, so you read your own words while Gemini never sees them:

- **Chat** (your messages and the page's text): email addresses, phone numbers (international with `+`, US, Singapore 4-4, or after "phone", "mobile" and the like), NRIC/FIN, SSNs and numbers after "passport" or "licence", card numbers (Luhn-checked), IBANs (checksum-checked), account numbers after "account", API keys and values after "password", "PIN" or "token", street addresses, unit numbers and Singapore postal codes, dates of birth after "born" or "DOB", and IP addresses. With AI Privacy on, also share counts ("500 shares") and amounts you tie to yourself ("I bought at $120", "my net worth is 300k"). The chat shows what was hidden above the answer.
- **Assessments and evaluations**, which are built from market data: only the patterns that can't be mistaken for a figure (emails, keys and passwords, grouped card numbers, IBANs, NRIC/FIN, SSNs).
- **Your own words**, everywhere: **Settings → Hidden from Gemini** lists words to always hide (matched whole-word, ignoring case), such as your name, family, employer or street, since names can't be found by pattern. Your account email is always included.

Pattern matching is a safety net, not a guarantee: a detail written in an unusual form (a phone number spelled out, an address without a street word) can get through. Tool results (market data) aren't redacted.

**SERPapi**
1. Sign up at [serpapi.com](https://serpapi.com/). The free plan includes a monthly allowance of searches (250 at the time of writing).
2. Add `SERP_API_KEY=…` to `.env`.
3. Run `python3 setup_sentiment.py` to install the NLTK data, load the financial-news model and test the key.

A Sentiment run uses 1 search per source (2 with "Both"; Google Finance is skipped, and not charged, for exchanges it doesn't cover). An AI Assessment with sentiment on uses 2, and so does a chat question about news. Checking your quota uses none.

**Ollama** (optional local model)
1. Install [Ollama](https://ollama.com) and open the app (it starts at login by default).
2. Run `ollama pull qwen3.5:9b` (7.6 GB), or pull another model and set `OLLAMA_MODEL`.

The local model is the chat's default and runs the scheduled assessments (see [Features → Scheduled assessments](FEATURES.md#scheduled-assessments)). Without it, chat can still use Gemini.

## Accounts

- **Fresh install:** if `data/users.json` doesn't exist, the API creates an **admin** account on first start, with the password from `ADMIN_PASSWORD` or a random one printed to the API console. Change it after signing in (**Settings → Change Password**).
- **Signing up:** anyone who can reach the app can create a `user` account at `/signup`, unless `ALLOW_SIGNUP=0`. Admins can create users or admins in **Settings → Users**.
- **Passwords** must be 10–128 characters, must not contain the username, and must not be a common password.
- **Roles:**

  | Role | Can do |
  |---|---|
  | `user` | Manage their own portfolio and history |
  | `admin` | Everything a user can, plus manage users, see every file in `data/`, and delete old usage records |

- **Data separation:** each user has their own holdings and AI history. The base currency setting and the AI usage log are shared by everyone.
- **Email:** each account can have one linked email (**Settings → Email**, which asks for your current password). Admins can add one when creating a user. An email can belong to only one account.

## Password reset

1. On the sign-in page, choose **Forgot password?** and enter your username or linked email.
2. A reset link is created that **works once and expires in 30 minutes**. Using it, or changing the password any other way, invalidates it.
3. It is delivered:
   - **by email**, when `SMTP_HOST` is set and the account has an email;
   - **otherwise to the API server's terminal**, the window where you ran `./dev.sh`. This keeps recovery working on a local install with no mail server, and only someone with access to the machine can see it.
4. Choosing a new password signs the account out everywhere else.

The request page shows the same message whether or not the account exists, so it can't be used to discover usernames. Each account can request one link per minute.

**Sending real email with Gmail:** turn on 2-Step Verification, create an app password at [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords), then set:

```
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=you@gmail.com
SMTP_PASSWORD=<16-character app password>
SMTP_FROM=Portfolio Dashboard <you@gmail.com>
```

**Sending with a Microsoft 365 / Outlook account** (for example a university address):

```
SMTP_HOST=smtp.office365.com
SMTP_PORT=587
SMTP_USER=you@your-school.edu
SMTP_PASSWORD=<your password, or an app password if your organization uses MFA>
SMTP_FROM=Portfolio Dashboard <you@your-school.edu>
```

Many organizations disable password-based SMTP for their accounts. If the test reports `535 5.7.139` or `Authentication unsuccessful`, your IT department has turned it off; use a personal Gmail account with an app password instead.

Check your settings with `python3 -m backend.manage test-email you@example.com`, then restart the API (it reads `.env` only at startup). If sending fails during a reset, the error is logged and the link falls back to the console. TLS uses `certifi`'s certificate bundle, so it also works with the python.org macOS build of Python, which has no system certificates.

**From the command line** (run on the machine hosting the API, from the repository root):

```bash
python3 -m backend.manage users                          # list accounts and emails
python3 -m backend.manage set-email admin you@example.com
python3 -m backend.manage reset-link admin               # prints a 30-minute link
```

**Last resort:** stop the API, delete `data/users.json`, and restart. That recreates only the admin account (with a new printed password, or `ADMIN_PASSWORD`), so other accounts are lost, but portfolios stay on disk and reappear if you recreate a user with the same username.

## Deployment

The app runs as two processes. A minimal production setup:

```bash
pip install -r requirements.txt
export SESSION_SECRET="$(python3 -c 'import secrets; print(secrets.token_urlsafe(48))')"
export ALLOW_SIGNUP=0     # optional: invite-only
python3 -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 &

cd web && npm ci && npm run build
API_URL=http://127.0.0.1:8000 npm start      # serves on :3000
```

Put an HTTPS reverse proxy in front of port 3000 only. The API should not be reachable directly from the internet, since the web app proxies to it.

- **Run one API worker.** Caches are in memory, and the JSON store has no cross-process locking.
- **Allow long requests.** AI assessments and model training can take 10–60 seconds. The web app allows 180s (`experimental.proxyTimeout` in `web/next.config.ts`); give any outer proxy at least that much.
- **Back up `data/`.** It holds every account, portfolio and AI recommendation.

## Security notes

- **Password hashing** is PBKDF2-SHA256 (600,000 iterations, per-user salt). Accounts from the original app (salted SHA-256) still sign in and are re-hashed at their next successful login. Failed sign-ins take the same time whether or not the username exists.
- **Rate limits:** 5 failed password checks per account and IP, or 30 per IP, within 15 minutes, block further attempts for that window (sign-in, change password, change email). Sign-up allows 5 accounts per IP per hour; forgot-password 10 requests per IP per hour. Counts are kept in memory per API process, so with several instances add a shared limit at the edge too.
- **CSRF:** cookies are `SameSite=Lax`, and the API rejects any `POST`/`PUT`/`PATCH`/`DELETE` without an `X-Requested-With` header, which other sites can't add to a cross-origin request.
- **Headers:** the web app sends HSTS, `X-Frame-Options: DENY`, `frame-ancestors 'none'`, `nosniff`, `Referrer-Policy: no-referrer` (keeps reset tokens out of referrers) and a restrictive `Permissions-Policy`. API responses are `Cache-Control: no-store`.
- **Sign-up is open by default.** Set `ALLOW_SIGNUP=0` if the app is reachable by others and you don't want strangers creating accounts.
- **Sessions** are signed and carry the account's session version. Changing or resetting a password bumps that version, signing out every other session. Signing out on one device clears only that cookie. Rotating `SESSION_SECRET` invalidates every session and every outstanding reset link.
- **Reset links** are signed, time-limited (30 minutes) and tied to the current password hash, so nothing needs to be stored server-side and each link works only once.
- **Secrets stay out of git.** `.env`, `data/` and `*.json` data files are git-ignored. Never commit API keys.
