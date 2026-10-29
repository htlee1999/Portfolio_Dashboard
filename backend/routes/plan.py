from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from config import SUPPORTED_CURRENCIES

from .. import plan
from ..auth import current_user
from ..storage import load_plan
from ..utils import clean

router = APIRouter(prefix="/api/plan", tags=["plan"])


class TargetsIn(BaseModel):
    targets: dict[str, float]
    band: float | None = Field(None, gt=0, le=50)


class WatchIn(BaseModel):
    symbol: str = Field(min_length=1, max_length=20)


class ThesisIn(BaseModel):
    thesis: str = Field("", max_length=4000)
    sell_if: list[str] = Field(default_factory=list, max_length=20)
    review_date: date | None = None


class AlertIn(BaseModel):
    symbol: str = Field(min_length=1, max_length=20)
    kind: str
    value: float
    note: str | None = Field(None, max_length=200)


@router.get("")
def get_plan(user: dict = Depends(current_user)):
    return load_plan(user["username"])


@router.get("/status")
def get_status(base: str = "USD", user: dict = Depends(current_user)):
    if base.upper() not in SUPPORTED_CURRENCIES:
        raise HTTPException(400, f"Unsupported currency {base}")
    return clean(plan.status(user["username"], base.upper()))


@router.put("/targets")
def put_targets(body: TargetsIn, user: dict = Depends(current_user)):
    if sum(v for v in body.targets.values() if v and v > 0) > 100.0001:
        raise HTTPException(400, "Targets add up to more than 100%")
    if any(v < 0 or v > 100 for v in body.targets.values()):
        raise HTTPException(400, "Each target must be between 0 and 100%")
    return plan.set_targets(user["username"], body.targets, body.band)


@router.post("/watchlist", status_code=201)
def add_watch(body: WatchIn, user: dict = Depends(current_user)):
    return plan.add_watch(user["username"], body.symbol)


@router.delete("/watchlist/{symbol}")
def remove_watch(symbol: str, user: dict = Depends(current_user)):
    return plan.remove_watch(user["username"], symbol)


@router.put("/journal/{symbol}")
def put_thesis(symbol: str, body: ThesisIn, user: dict = Depends(current_user)):
    return plan.set_thesis(user["username"], symbol, body.thesis, body.sell_if,
                           body.review_date.isoformat() if body.review_date else None)


@router.delete("/journal/{symbol}")
def delete_thesis(symbol: str, user: dict = Depends(current_user)):
    return plan.delete_thesis(user["username"], symbol)


@router.post("/alerts", status_code=201)
def add_alert(body: AlertIn, user: dict = Depends(current_user)):
    try:
        return plan.add_alert(user["username"], body.symbol, body.kind, body.value, body.note)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.delete("/alerts/{alert_id}")
def delete_alert(alert_id: str, user: dict = Depends(current_user)):
    return plan.delete_alert(user["username"], alert_id)
