# Data

Everything is stored as JSON in `data/` at the repository root. The directory is created automatically and is git-ignored. All writes go through `backend/storage.py`, which writes to a temp file and renames it, so a crash can't leave a half-written file.

```
data/
├── users.json                         # accounts (shared)
├── settings.json                      # app settings (shared)
├── gemini_usage.json                  # AI call log, Gemini and local model (shared)
├── scheduled_runs.json                # summary of each scheduled run (last 200)
├── scheduled_status.json              # progress of the current or last scheduled run
├── portfolio_<username>.json          # holdings, one file per user
├── recommendation_history_<username>.json   # AI assessments, one file per user
├── assessment_inputs_<username>.jsonl       # each assessment's full prompt and context, one line per call
├── logs/scheduled.log                 # output of scheduled runs
├── backups/
│   └── portfolio_backup_<username>_<YYYYMMDD_HHMMSS>.json
└── .session_secret                    # cookie signing key (if SESSION_SECRET isn't set)
```

Files from older versions (`portfolio.json`, `exports/`, and so on) are ignored by the current app and can be deleted.

## `portfolio_<username>.json`

```json
{
  "last_updated": "2026-10-01T11:06:58.923408",
  "username": "admin",
  "holdings": [
    {
      "Symbol": "AMD",
      "Quantity": 42.0,
      "Purchase_Price": 110.78,
      "Purchase_Date": "2025-04-04",
      "Currency": "USD"
    }
  ]
}
```

Each entry is one purchase lot, and the same symbol may appear many times. `Symbol` is stored in normalized form (see `config.TICKER_ALIASES`). `Currency` is the currency the lot was bought in, which is also the currency its price is quoted in.

## `settings.json`

```json
{ "base_currency": "USD", "last_updated": "2026-10-02T09:00:00" }
```

## `users.json`

```json
{
  "admin": {
    "password_hash": "<sha256 hex>",
    "role": "admin",
    "email": "you@example.com",
    "session_version": 1,
    "created_at": "2025-09-19T10:00:00",
    "last_login": "2026-10-01T11:03:00"
  }
}
```

`email` is optional, stored lower-case, and unique across accounts. `session_version` increases with every password change or reset; sessions issued under an older version are rejected. Accounts without these fields behave as having no email and version 0.

## `recommendation_history_<username>.json`

An array, appended once per AI assessment:

```json
[
  {
    "timestamp": "2026-10-02T10:15:00",
    "symbol": "AMD",
    "recommendation": "HOLD",
    "confidence": 7,
    "price_at_signal": 615.73,
    "price_target": 650.0,
    "time_horizon": "Medium-term",
    "strengths": ["..."],
    "risks": ["..."],
    "reasoning": "One-paragraph summary",
    "steps": [{ "title": "Technical picture", "content": "..." }],
    "position_advice": "...",
    "portfolio_context": { "avg_purchase_price": 121.28, "total_quantity": 98, "unrealized_pct": 407.7 },
    "quote_date": "2026-10-01",
    "model": "gemini-3.5-flash-lite",
    "provider": "gemini",
    "source": "manual",
    "run": null,
    "prompt_version": 2,
    "rule_inputs": { "analyst": "buy", "app_score": 64.2 },
    "evaluation": { "verdict": "weakened", "confidence_adjusted": 5, "summary": "...", "findings": [...],
                    "counter_case": "...", "invalidation": [...], "entry_plan": null,
                    "skills": ["claim-check", "counter-case", "..."], "generated_at": "..." }
  }
]
```

`evaluation` is present only when **Evaluate** was run on that assessment. `provider` is `gemini` or `local`; `source` is `manual` or `scheduled`, and scheduled calls carry their `run` (both models' calls in a comparison run share it). `rule_inputs` feeds the Track Record's simple rules. Records from before prompt version 2 have none of the fields from `quote_date` to `rule_inputs`. `timestamp` identifies the record: it equals the assessment's `generated_at`.

Records written by the original Streamlit version have no `steps` or `position_advice`, and `reasoning` holds the full AI response. The Track Record handles both shapes.

## `gemini_usage.json`

An array with one record per AI call, on Gemini or the local model:

```json
{
  "timestamp": "2026-10-02T10:15:00",
  "model": "gemini-3.5-flash-lite",
  "input_tokens": 812,
  "output_tokens": 1450,
  "total_tokens": 2262,
  "cost_usd": 0.0005,
  "operation": "investment_assessment",
  "symbol": "AMD",
  "success": true,
  "error_message": null
}
```

`operation` is `investment_assessment`, `assessment_evaluation` or `chat`. `symbol` is null for a chat asked with no symbol selected. Calls to models not in `usage.PRICING`, such as the local model, have a `cost_usd` of 0.

## Backups

**Holdings → Create Backup** writes your holdings and the shared settings:

```json
{ "portfolio": [ /* holdings */ ], "settings": { /* settings.json */ }, "backup_created": "..." }
```

To restore, copy the `portfolio` array into `holdings` in **Settings → Data → Edit portfolio JSON**, or import an exported CSV on the Holdings page.

## Editing by hand

Use **Settings → Data → Edit portfolio JSON** rather than editing files while the API is running. The editor checks that `holdings` is an array and that every entry has `Symbol`, `Quantity`, `Purchase_Price` and `Purchase_Date`, with numeric quantities and prices.
