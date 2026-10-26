import re
from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException

from config import normalize_symbol

from .. import retro_markets, retrograde
from ..auth import current_user

router = APIRouter(prefix="/api", tags=["astro"])


@router.get("/retrograde")
def retrograde_calendar(start_year: int | None = None, end_year: int | None = None, refresh: bool = False,
                        user: dict = Depends(current_user)):
    this_year = date.today().year
    start_year = start_year or this_year - 1
    end_year = end_year or this_year + 1
    if not (retrograde.MIN_YEAR <= start_year <= end_year <= retrograde.MAX_YEAR) \
            or end_year - start_year >= retrograde.MAX_SPAN:
        raise HTTPException(400, f"Years must be {retrograde.MIN_YEAR}–{retrograde.MAX_YEAR}, "
                                 f"spanning at most {retrograde.MAX_SPAN} years")
    try:
        return retrograde.calendar(start_year, end_year, refresh)
    except RuntimeError as e:
        raise HTTPException(502, str(e)) from e


_SYMBOL = re.compile(r"^[A-Za-z0-9.\-^=]{1,20}$")


@router.get("/retrograde/etfs")
def retrograde_etfs(user: dict = Depends(current_user)):
    return {"etfs": [{"symbol": s, "name": n, "group": g} for s, n, g in retro_markets.ETFS],
            "benchmark": retro_markets.BENCHMARK}


@router.get("/retrograde/markets")
def retrograde_markets(planets: str = "mercury,venus,mars", symbols: str = "", since: int = 2000,
                       window: Literal["retrograde", "shadow"] = "retrograde", user: dict = Depends(current_user)):
    known = {pid for pid, *_ in retrograde.PLANETS}
    chosen = [p for p in dict.fromkeys(planets.lower().split(",")) if p]
    if not chosen or any(p not in known for p in chosen):
        raise HTTPException(400, f"planets must be from {', '.join(sorted(known))}")
    syms = [normalize_symbol(s) for s in dict.fromkeys(symbols.upper().split(",")) if s]
    if len(syms) > 25 or any(not _SYMBOL.match(s) for s in syms):
        raise HTTPException(400, "Up to 25 valid symbols")
    if not 2000 <= since <= date.today().year - 2:
        raise HTTPException(400, f"since must be 2000–{date.today().year - 2}")
    order = [pid for pid, *_ in retrograde.PLANETS]
    try:
        return retro_markets.cached_analysis(tuple(syms or [s for s, *_ in retro_markets.ETFS]),
                                             tuple(sorted(chosen, key=order.index)), since, window)
    except RuntimeError as e:
        raise HTTPException(502, str(e)) from e
