"""JSON file persistence.

Reads and writes the same files under ``data/`` as the original Streamlit app (main branch),
so existing portfolios, settings, and AI history carry over unchanged.
"""

import fcntl
import json
import os
from contextlib import contextmanager
from datetime import datetime
from typing import Any

import pandas as pd

from config import PORTFOLIO_COLUMNS, normalize_symbol

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")


def data_path(*parts: str) -> str:
    os.makedirs(DATA_DIR, exist_ok=True)
    return os.path.join(DATA_DIR, *parts)


def load_json(path: str, default: Any) -> Any:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def save_json(path: str, data: Any) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = f"{path}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)
    os.replace(tmp, path)


def stamp() -> str:
    return datetime.now().isoformat()


def file_stamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


# ── Portfolio ────────────────────────────────────────────────────────────────

def portfolio_path(username: str) -> str:
    return data_path(f"portfolio_{username}.json")


def load_holdings(username: str) -> list[dict]:
    data = load_json(portfolio_path(username), {})
    holdings = data.get("holdings", []) if isinstance(data, dict) else []
    out = []
    for h in holdings:
        row = {col: h.get(col) for col in PORTFOLIO_COLUMNS}
        row["Currency"] = row["Currency"] or "USD"
        row["Purchase_Date"] = str(row["Purchase_Date"])[:10] if row["Purchase_Date"] else None
        out.append(row)
    return out


def save_holdings(username: str, holdings: list[dict]) -> None:
    save_json(portfolio_path(username), {
        "last_updated": stamp(),
        "username": username,
        "holdings": holdings,
    })


def holdings_frame(username: str) -> pd.DataFrame:
    return pd.DataFrame(load_holdings(username), columns=PORTFOLIO_COLUMNS)


def add_holding(username: str, symbol: str, quantity: float, price: float,
                purchase_date: str, currency: str) -> None:
    holdings = load_holdings(username)
    holdings.append({
        "Symbol": normalize_symbol(symbol),
        "Quantity": float(quantity),
        "Purchase_Price": float(price),
        "Purchase_Date": purchase_date,
        "Currency": currency,
    })
    save_holdings(username, holdings)


def remove_holding_at(username: str, index: int) -> bool:
    holdings = load_holdings(username)
    if not 0 <= index < len(holdings):
        return False
    holdings.pop(index)
    save_holdings(username, holdings)
    return True


def import_csv_rows(username: str, frame: pd.DataFrame) -> int:
    required = ["Symbol", "Quantity", "Purchase_Price", "Purchase_Date"]
    missing = [c for c in required if c not in frame.columns]
    if missing:
        raise ValueError(f"CSV is missing columns: {', '.join(missing)}")
    if "Currency" not in frame.columns:
        frame["Currency"] = "USD"
    frame["Symbol"] = frame["Symbol"].astype(str).apply(normalize_symbol)
    frame["Purchase_Date"] = pd.to_datetime(frame["Purchase_Date"]).dt.strftime("%Y-%m-%d")
    frame["Quantity"] = frame["Quantity"].astype(float)
    frame["Purchase_Price"] = frame["Purchase_Price"].astype(float)
    frame["Currency"] = frame["Currency"].fillna("USD").astype(str).str.upper()
    new_rows = frame[PORTFOLIO_COLUMNS].to_dict("records")
    save_holdings(username, load_holdings(username) + new_rows)
    return len(new_rows)


# ── Sales ────────────────────────────────────────────────────────────────────
# Lots stay the shares you hold now, so everything that reads them is unchanged. A sale takes shares
# from the oldest lots first (FIFO) and records the lots it used, so it can be undone and its gain
# and the original purchases rebuilt.

def transactions_path(username: str) -> str:
    return data_path(f"transactions_{username}.json")


def load_transactions(username: str) -> list[dict]:
    data = load_json(transactions_path(username), [])
    return data if isinstance(data, list) else []


def save_transactions(username: str, transactions: list[dict]) -> None:
    save_json(transactions_path(username), transactions)


# Shares below this are rounding left over from a sale, not a holding.
_DUST = 1e-9


def sell(username: str, symbol: str, quantity: float, price: float, sale_date: str, fees: float = 0.0) -> dict:
    """Sell ``quantity`` shares from the oldest lots bought on or before ``sale_date``. Raises ValueError
    when fewer shares were held. The price is in the lots' currency."""
    symbol = normalize_symbol(symbol)
    holdings = load_holdings(username)
    eligible = sorted((i for i, h in enumerate(holdings) if h["Symbol"] == symbol and (h["Purchase_Date"] or "") <= sale_date),
                      key=lambda i: holdings[i]["Purchase_Date"] or "")
    held = sum(float(holdings[i]["Quantity"]) for i in eligible)
    if quantity > held + _DUST:
        raise ValueError(f"You held {held:g} {symbol} shares on {sale_date}, fewer than {quantity:g}")
    currencies = {holdings[i]["Currency"] for i in eligible}
    if len(currencies) > 1:
        raise ValueError(f"{symbol} lots are in more than one currency ({', '.join(sorted(currencies))})")

    left, used, cost = quantity, [], 0.0
    for i in eligible:
        if left <= _DUST:
            break
        lot = holdings[i]
        take = min(left, float(lot["Quantity"]))
        used.append({"Purchase_Date": lot["Purchase_Date"], "Purchase_Price": float(lot["Purchase_Price"]),
                     "Quantity": take, "Currency": lot["Currency"]})
        cost += take * float(lot["Purchase_Price"])
        lot["Quantity"] = float(lot["Quantity"]) - take
        left -= take
    holdings = [h for h in holdings if float(h["Quantity"]) > _DUST]

    proceeds = quantity * price - fees
    record = {
        "id": file_stamp() + f"_{len(load_transactions(username))}",
        "type": "SELL",
        "Symbol": symbol,
        "Quantity": float(quantity),
        "Price": float(price),
        "Fees": float(fees),
        "Date": sale_date,
        "Currency": currencies.pop() if currencies else "USD",
        "lots": used,
        "cost": cost,
        "proceeds": proceeds,
        "realized": proceeds - cost,
        "created": stamp(),
    }
    save_holdings(username, holdings)
    save_transactions(username, load_transactions(username) + [record])
    return record


def undo_sell(username: str, transaction_id: str) -> bool:
    """Delete a sale and put the shares it took back into the lots they came from."""
    transactions = load_transactions(username)
    record = next((t for t in transactions if t.get("id") == transaction_id), None)
    if record is None:
        return False
    holdings = load_holdings(username)
    for lot in record.get("lots", []):
        match = next((h for h in holdings if h["Symbol"] == record["Symbol"] and h["Purchase_Date"] == lot["Purchase_Date"]
                      and float(h["Purchase_Price"]) == lot["Purchase_Price"]), None)
        if match:
            match["Quantity"] = float(match["Quantity"]) + lot["Quantity"]
        else:
            holdings.append({"Symbol": record["Symbol"], **lot})
    save_holdings(username, holdings)
    save_transactions(username, [t for t in transactions if t.get("id") != transaction_id])
    return True


def all_purchases(username: str) -> list[dict]:
    """Every purchase as it was made: the lots held now plus the parts of lots since sold."""
    out = [dict(h) for h in load_holdings(username)]
    for t in load_transactions(username):
        if t.get("type") == "SELL":
            out += [{"Symbol": t["Symbol"], **lot} for lot in t.get("lots", [])]
    return out


# ── Plan: target weights, watchlist, thesis journal and alert rules ──────────

PLAN_DEFAULT = {"targets": {}, "band": 5.0, "watchlist": [], "journal": {}, "alerts": []}


def plan_path(username: str) -> str:
    return data_path(f"plan_{username}.json")


def load_plan(username: str) -> dict:
    data = load_json(plan_path(username), {})
    return {**PLAN_DEFAULT, **(data if isinstance(data, dict) else {})}


def save_plan(username: str, plan: dict) -> dict:
    plan = {**PLAN_DEFAULT, **plan, "last_updated": stamp()}
    save_json(plan_path(username), plan)
    return plan


def portfolio_last_updated(username: str) -> str | None:
    data = load_json(portfolio_path(username), {})
    return data.get("last_updated") if isinstance(data, dict) else None


def backup(username: str) -> str:
    path = data_path("backups", f"portfolio_backup_{username}_{file_stamp()}.json")
    save_json(path, {
        "portfolio": load_holdings(username),
        "transactions": load_transactions(username),
        "plan": load_plan(username),
        "settings": load_settings(),
        "backup_created": stamp(),
    })
    return os.path.basename(path)


# ── Settings (shared, as in the original app) ────────────────────────────────

def load_settings() -> dict:
    return load_json(data_path("settings.json"), {"base_currency": "USD"})


def save_settings(settings: dict) -> dict:
    settings = {**settings, "last_updated": stamp()}
    save_json(data_path("settings.json"), settings)
    return settings


# ── AI recommendation history ────────────────────────────────────────────────

def history_path(username: str) -> str:
    return data_path(f"recommendation_history_{username}.json")


def load_history(username: str) -> list[dict]:
    return load_json(history_path(username), [])


@contextmanager
def _history_lock(username: str):
    """Scheduled runs write the history from their own process, so read-modify-write needs a file lock."""
    with open(history_path(username) + ".lock", "w") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)


def append_history(username: str, record: dict) -> None:
    with _history_lock(username):
        history = load_history(username)
        history.append(record)
        save_json(history_path(username), history)


def inputs_path(username: str) -> str:
    return data_path(f"assessment_inputs_{username}.jsonl")


def append_inputs(username: str, record: dict) -> None:
    """One JSON line per assessment: the prompt and context it was given. Append-only, and kept out of
    the history file so the Track Record doesn't load it."""
    with open(inputs_path(username), "a", encoding="utf-8") as f:
        f.write(json.dumps(record, default=str) + "\n")


def load_inputs(username: str) -> list[dict]:
    try:
        with open(inputs_path(username), encoding="utf-8") as f:
            return [json.loads(line) for line in f if line.strip()]
    except FileNotFoundError:
        return []


def update_history(username: str, symbol: str, timestamp: str, fields: dict) -> bool:
    """Merge ``fields`` into the record for ``symbol`` saved at ``timestamp``. False if none matches."""
    with _history_lock(username):
        history = load_history(username)
        for record in history:
            if record.get("symbol") == symbol and record.get("timestamp") == timestamp:
                record.update(fields)
                save_json(history_path(username), history)
                return True
    return False
