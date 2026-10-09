"""JSON file persistence.

Reads and writes the same files under ``data/`` as the original Streamlit app (main branch),
so existing portfolios, settings, and AI history carry over unchanged.
"""

import json
import os
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


def portfolio_last_updated(username: str) -> str | None:
    data = load_json(portfolio_path(username), {})
    return data.get("last_updated") if isinstance(data, dict) else None


def backup(username: str) -> str:
    path = data_path("backups", f"portfolio_backup_{username}_{file_stamp()}.json")
    save_json(path, {
        "portfolio": load_holdings(username),
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


def append_history(username: str, record: dict) -> None:
    history = load_history(username)
    history.append(record)
    save_json(history_path(username), history)


def update_history(username: str, symbol: str, timestamp: str, fields: dict) -> bool:
    """Merge ``fields`` into the record for ``symbol`` saved at ``timestamp``. False if none matches."""
    history = load_history(username)
    for record in history:
        if record.get("symbol") == symbol and record.get("timestamp") == timestamp:
            record.update(fields)
            save_json(history_path(username), history)
            return True
    return False
