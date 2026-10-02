import csv
import io
import json
import os
from datetime import datetime

from fastapi import APIRouter, Body, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

from .. import auth, storage, usage
from ..auth import admin_user, current_user
from ..utils import clean

router = APIRouter(prefix="/api", tags=["admin"])


@router.get("/usage")
def get_usage(days: int = 30, user: dict = Depends(current_user)):
    return clean(usage.summary(max(1, min(days, 3650))))


@router.delete("/usage/old")
def clear_old_usage(days: int = 90, user: dict = Depends(admin_user)):
    return {"removed": usage.clear_older_than(days)}


@router.get("/usage/export")
def export_usage(days: int = 30, user: dict = Depends(current_user)):
    rows = usage.export_rows(days)
    buf = io.StringIO()
    fields = ["timestamp", "model", "operation", "symbol", "input_tokens", "output_tokens",
              "total_tokens", "cost_usd", "success", "error_message"]
    writer = csv.DictWriter(buf, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    name = f"gemini_usage_{datetime.now():%Y%m%d}.csv"
    return Response(buf.getvalue(), media_type="text/csv", headers={"Content-Disposition": f'attachment; filename="{name}"'})


@router.get("/data/stats")
def data_stats(user: dict = Depends(current_user)):
    holdings = storage.load_holdings(user["username"])
    path = storage.portfolio_path(user["username"])
    files = []
    for root, _, names in os.walk(storage.DATA_DIR):
        for name in sorted(names):
            if name.startswith("."):
                continue
            full = os.path.join(root, name)
            rel = os.path.relpath(full, storage.DATA_DIR)
            # Non-admins only see their own files.
            if user["role"] != "admin" and user["username"] not in name and rel != "settings.json":
                continue
            files.append({
                "path": rel,
                "size": os.path.getsize(full),
                "modified": datetime.fromtimestamp(os.path.getmtime(full)).isoformat(),
                "mine": f"_{user['username']}" in name,
            })
    return {
        "username": user["username"],
        "holdings": len(holdings),
        "symbols": sorted({h["Symbol"] for h in holdings}),
        "currencies": sorted({h["Currency"] for h in holdings}),
        "last_updated": storage.portfolio_last_updated(user["username"]),
        "portfolio_file": os.path.basename(path),
        "files": sorted(files, key=lambda f: f["path"]),
    }


@router.get("/data/raw")
def raw_portfolio(user: dict = Depends(current_user)):
    return storage.load_json(storage.portfolio_path(user["username"]), {"holdings": []})


@router.put("/data/raw")
def put_raw_portfolio(doc: dict = Body(...), user: dict = Depends(current_user)):
    holdings = doc.get("holdings")
    if not isinstance(holdings, list):
        raise HTTPException(400, 'JSON must contain a "holdings" array')
    required = {"Symbol", "Quantity", "Purchase_Price", "Purchase_Date"}
    for i, h in enumerate(holdings):
        if not isinstance(h, dict) or not required <= h.keys():
            raise HTTPException(400, f"Holding {i} must have {', '.join(sorted(required))}")
        try:
            float(h["Quantity"]), float(h["Purchase_Price"])
        except (TypeError, ValueError):
            raise HTTPException(400, f"Holding {i}: Quantity and Purchase_Price must be numbers")
    storage.save_holdings(user["username"], holdings)
    return {"ok": True}


class NewUser(BaseModel):
    username: str
    password: str
    role: str = "user"
    email: str | None = None


@router.get("/users")
def users(user: dict = Depends(admin_user)):
    return auth.list_users()


@router.post("/users", status_code=201)
def create_user(body: NewUser, user: dict = Depends(admin_user)):
    if body.role not in ("user", "admin"):
        raise HTTPException(400, "role must be 'user' or 'admin'")
    try:
        auth.create_user(body.username, body.password, body.role, body.email)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"ok": True}
