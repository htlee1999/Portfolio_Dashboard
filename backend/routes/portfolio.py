import io
from datetime import date

import pandas as pd
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, Field

from config import PERIOD_LIST, SUPPORTED_CURRENCIES

from .. import portfolio, storage
from ..auth import current_user
from ..utils import clean

router = APIRouter(prefix="/api", tags=["portfolio"])


class HoldingIn(BaseModel):
    symbol: str = Field(min_length=1, max_length=20)
    quantity: float = Field(gt=0)
    purchase_price: float = Field(gt=0)
    purchase_date: date
    currency: str = "USD"


class SettingsIn(BaseModel):
    base_currency: str


def _check_currency(code: str) -> str:
    code = code.upper()
    if code not in SUPPORTED_CURRENCIES:
        raise HTTPException(400, f"Unsupported currency {code}")
    return code


def _check_period(period: str) -> str:
    if period not in PERIOD_LIST:
        raise HTTPException(400, f"period must be one of {', '.join(PERIOD_LIST)}")
    return period


@router.get("/meta")
def meta():
    return {"currencies": SUPPORTED_CURRENCIES, "periods": PERIOD_LIST}


@router.get("/settings")
def get_settings(user: dict = Depends(current_user)):
    return storage.load_settings()


@router.put("/settings")
def put_settings(body: SettingsIn, user: dict = Depends(current_user)):
    settings = storage.load_settings()
    settings["base_currency"] = _check_currency(body.base_currency)
    return storage.save_settings(settings)


@router.get("/holdings")
def list_holdings(user: dict = Depends(current_user)):
    holdings = storage.load_holdings(user["username"])
    return {
        "holdings": [{"index": i, **h} for i, h in enumerate(holdings)],
        "last_updated": storage.portfolio_last_updated(user["username"]),
    }


@router.post("/holdings", status_code=201)
def add_holding(body: HoldingIn, user: dict = Depends(current_user)):
    storage.add_holding(user["username"], body.symbol, body.quantity, body.purchase_price,
                        body.purchase_date.isoformat(), _check_currency(body.currency))
    return {"ok": True}


@router.delete("/holdings/{index}")
def delete_holding(index: int, user: dict = Depends(current_user)):
    if not storage.remove_holding_at(user["username"], index):
        raise HTTPException(404, "Holding not found")
    return {"ok": True}


@router.delete("/holdings")
def clear_holdings(user: dict = Depends(current_user)):
    storage.save_holdings(user["username"], [])
    return {"ok": True}


@router.post("/holdings/import")
async def import_holdings(file: UploadFile = File(...), user: dict = Depends(current_user)):
    try:
        frame = pd.read_csv(io.BytesIO(await file.read()))
        count = storage.import_csv_rows(user["username"], frame)
    except Exception as e:
        raise HTTPException(400, f"Could not import CSV: {e}")
    return {"imported": count}


@router.get("/holdings/export")
def export_holdings(user: dict = Depends(current_user)):
    csv = storage.holdings_frame(user["username"]).to_csv(index=False)
    name = f"portfolio_{user['username']}_{storage.file_stamp()}.csv"
    return Response(csv, media_type="text/csv", headers={"Content-Disposition": f'attachment; filename="{name}"'})


@router.get("/holdings/template")
def csv_template():
    csv = ("Symbol,Quantity,Purchase_Price,Purchase_Date,Currency\n"
           "AAPL,10,150.00,2024-01-01,USD\nGOOGL,5,2500.00,2024-01-15,SGD\nMSFT,15,300.00,2024-02-01,USD\n")
    return Response(csv, media_type="text/csv", headers={"Content-Disposition": 'attachment; filename="portfolio_template.csv"'})


@router.post("/holdings/backup")
def backup(user: dict = Depends(current_user)):
    return {"file": storage.backup(user["username"])}


@router.get("/portfolio/metrics")
def portfolio_metrics(base: str = "USD", user: dict = Depends(current_user)):
    return clean(portfolio.metrics(user["username"], _check_currency(base)))


@router.get("/portfolio/performance")
def portfolio_performance(base: str = "USD", period: str = "1y", user: dict = Depends(current_user)):
    return clean(portfolio.performance(user["username"], _check_currency(base), _check_period(period)))
