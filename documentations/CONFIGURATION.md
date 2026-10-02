# Configuration

## Environment variables

The API reads `.env` from the repository root at startup (`python-dotenv`). Copy `config.env.example` to `.env` and fill in what you need, then **restart the API** after any change.

| Variable | Default | Purpose |
|---|---|---|
| `FINN_API_KEY` | none | Finnhub real-time quotes for US-listed symbols. Without it, every quote comes from Yahoo Finance, which rate-limits aggressively |
| `GEMINI_API_KEY` | none | Enables AI Assessment |
| `SERP_API_KEY` | none | Enables Sentiment and the news input to AI Assessment |
| `SESSION_SECRET` | auto-generated | Key that signs session cookies, at least 32 characters. If unset, a random key is created in `data/.session_secret` on first run. **Required** on Vercel (or with `REQUIRE_SESSION_SECRET=1`) |
| `COOKIE_SECURE` | auto | Cookies are `Secure` whenever the request arrived over HTTPS. Set `1` to force on, `0` to force off |
| `ADMIN_PASSWORD` | generated | Password for the `admin` account created on a fresh install. If unset, a random one is printed to the API console |
| `ALLOW_SIGNUP` | `1` | Set to `0` to close public sign-up; admins can still create accounts in **Settings → Users** |
| `TRUST_PROXY` | off | Set to `1` only when the API sits behind a proxy that sets `X-Forwarded-For`, so rate limits apply per real client IP |
| `API_DOCS` | on (off on Vercel) | Serves interactive API docs at `/docs` |
| `SMTP_HOST`, `SMTP_PORT` (587), `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM` | none | Email delivery for password resets. Port 465 uses SSL; anything else uses STARTTLS |
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

The model is `gemini-2.5-flash` (`backend/assessment.py → MODEL`). Each assessment uses roughly 1,500–4,000 tokens. Free-tier limits and the cost estimates on API Usage are set in `backend/usage.py` (`RATE_LIMITS`, `PRICING`); update them if Google changes its pricing or you're on a paid plan.

**SERPapi**
1. Sign up at [serpapi.com](https://serpapi.com/). The free plan includes 100 searches per month.
2. Add `SERP_API_KEY=…` to `.env`.
3. Run `python3 setup_sentiment.py` to install the NLTK data and test the key.

A Sentiment run uses 1 search per source (2 with "Both"). An AI Assessment with sentiment on uses 2. Checking your quota uses none.

## Accounts

- **Fresh install:** if `data/users.json` doesn't exist, the API creates an **admin** account on first start, with the password from `ADMIN_PASSWORD` or a random one printed to the API console. Change it after signing in (**Settings → Change Password**).
- **Signing up:** anyone who can reach the app can create a `user` account at `/signup`, unless `ALLOW_SIGNUP=0`. Admins can create users or admins in **Settings → Users**.
- **Passwords** must be 10–128 characters, must not contain the username, and must not be a common password.
- **Roles:**

  | Role | Can do |
  |---|---|
  | `user` | Manage their own portfolio and history |
  | `admin` | Everything a user can, plus manage users, see every file in `data/`, and delete old usage records |

- **Data separation:** each user has their own holdings and AI history. The base currency setting and the Gemini usage log are shared by everyone.
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
