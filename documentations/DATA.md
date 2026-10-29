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
├── transactions_<username>.json       # sales, one file per user
├── plan_<username>.json               # target weights, watchlist, theses and alert rules
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

## `transactions_<username>.json`

An array of sales, appended by **Holdings → Record Sale**. The lots in `portfolio_<username>.json` stay the shares you hold now; a sale takes shares from the oldest lots first and records the pieces it took, so it can be undone and the original purchases rebuilt for Performance's actual returns.

```json
[
  {
    "id": "20261026_174507_0",
    "type": "SELL",
    "Symbol": "KO",
    "Quantity": 15.0,
    "Price": 65.0,
    "Fees": 5.0,
    "Date": "2024-06-03",
    "Currency": "USD",
    "lots": [
      { "Purchase_Date": "2022-01-05", "Purchase_Price": 50.0, "Quantity": 10.0, "Currency": "USD" },
      { "Purchase_Date": "2023-01-05", "Purchase_Price": 60.0, "Quantity": 5.0, "Currency": "USD" }
    ],
    "cost": 800.0,
    "proceeds": 970.0,
    "realized": 170.0,
    "created": "2026-10-26T17:45:07"
  }
]
```

`proceeds` is quantity × price − fees; `realized` is proceeds − cost, all in the lots' currency. Deleting a sale (the undo button) adds its `lots` back. If you edit lots by hand after a sale, an undo adds the shares back as a new lot when the original lot is gone.

## `plan_<username>.json`

```json
{
  "targets": { "AMD": 25, "NVDA": 15 },
  "band": 5.0,
  "watchlist": ["KO", "ASML"],
  "journal": {
    "AMD": {
      "thesis": "Data-centre GPU share gains",
      "sell_if": ["Data-centre revenue growth below 20% for two quarters"],
      "review_date": "2027-01-31",
      "created": "2026-10-26T18:00:00",
      "updated": "2026-10-26T18:00:00"
    }
  },
  "alerts": [
    { "id": "3f9c0a1b2d4e", "symbol": "AMD", "kind": "below_cost", "value": 20, "note": null, "created": "2026-10-26T18:01:00" }
  ],
  "last_updated": "2026-10-26T18:01:00"
}
```

`targets` are weights in percent; `band` is how many points a holding may drift before Plan suggests a trade. Alert `kind` is one of `price_above`, `price_below`, `below_cost`, `weight_above`, `drawdown` and `estimate_cut` (see the [API reference](API.md#plan)).

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
    "expected_excess": 4.0,
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
    "prompt_version": 3,
    "rule_inputs": { "analyst": "buy", "app_score": 64.2 },
    "evaluation": { "verdict": "weakened", "confidence_adjusted": 5, "summary": "...", "findings": [...],
                    "counter_case": "...", "invalidation": [...], "entry_plan": null,
                    "skills": ["claim-check", "counter-case", "..."], "generated_at": "..." }
  }
]
```

`evaluation` is present only when **Evaluate** was run on that assessment. `provider` is `gemini` or `local`; `source` is `manual` or `scheduled`, and scheduled calls carry their `run` (both models' calls in a comparison run share it). `rule_inputs` feeds the Track Record's simple rules. `expected_excess` (the call's expected return against the S&P 500 in percentage points, from prompt version 3) feeds its ranking. Records from before prompt version 2 have none of the fields from `quote_date` to `rule_inputs`. `timestamp` identifies the record: it equals the assessment's `generated_at`.

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

**Holdings → Create Backup** writes your holdings, sales, plan and the shared settings:

```json
{ "portfolio": [ /* holdings */ ], "transactions": [ /* sales */ ], "plan": { /* plan_<username>.json */ },
  "settings": { /* settings.json */ }, "backup_created": "..." }
```

To restore, copy the `portfolio` array into `holdings` in **Settings → Data → Edit portfolio JSON**, or import an exported CSV on the Holdings page. Copy `transactions` and `plan` into `transactions_<username>.json` and `plan_<username>.json` with the API stopped.

## Editing by hand

Use **Settings → Data → Edit portfolio JSON** rather than editing files while the API is running. The editor checks that `holdings` is an array and that every entry has `Symbol`, `Quantity`, `Purchase_Price` and `Purchase_Date`, with numeric quantities and prices.
