import re
from typing import Any, Literal

from fastapi import APIRouter, Body, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field

from config import ML_AVAILABLE, PERIOD_LIST, is_gemini_api_configured, normalize_symbol

from .. import assessment, evaluation, fundamentals, predictive, reports, sentiment, technical, track_record
from ..auth import current_user
from ..storage import file_stamp
from ..utils import clean

router = APIRouter(prefix="/api", tags=["analysis"])

_SYMBOL = re.compile(r"^[A-Za-z0-9.\-^=]{1,20}$")


def _symbol(raw: str) -> str:
    if not _SYMBOL.match(raw):
        raise HTTPException(400, "Invalid symbol")
    return normalize_symbol(raw)


def _period(period: str) -> str:
    if period not in PERIOD_LIST:
        raise HTTPException(400, f"period must be one of {', '.join(PERIOD_LIST)}")
    return period


def _unavailable(symbol: str):
    return HTTPException(502, f"Could not fetch market data for {symbol}. Check the symbol, or Yahoo Finance may be rate-limiting — try again shortly.")


@router.get("/features")
def features(user: dict = Depends(current_user)):
    return {"ml": ML_AVAILABLE, "gemini": is_gemini_api_configured(), "sentiment": sentiment.status(),
            "chronos": predictive.chronos_status()}


def _check_indicator_params(rsi_period: int, macd_fast: int, macd_slow: int, bb_period: int, bb_std: float) -> None:
    if not (5 <= rsi_period <= 30 and 5 <= macd_fast < macd_slow <= 50 and 10 <= bb_period <= 30 and 1 <= bb_std <= 3):
        raise HTTPException(400, "Indicator parameters out of range")


@router.get("/stocks/{symbol}/technical")
def technical_analysis(symbol: str, period: str = "1y", rsi_period: int = 14, macd_fast: int = 12,
                       macd_slow: int = 26, bb_period: int = 20, bb_std: float = 2.0,
                       user: dict = Depends(current_user)):
    symbol = _symbol(symbol)
    _check_indicator_params(rsi_period, macd_fast, macd_slow, bb_period, bb_std)
    result = technical.analyze(symbol, _period(period), rsi_period, macd_fast, macd_slow, bb_period, bb_std)
    if result is None:
        raise _unavailable(symbol)
    return clean(result)


@router.get("/stocks/{symbol}/technical/backtest")
def technical_backtest(symbol: str, rsi_period: int = 14, macd_fast: int = 12, macd_slow: int = 26,
                       bb_period: int = 20, bb_std: float = 2.0, user: dict = Depends(current_user)):
    symbol = _symbol(symbol)
    _check_indicator_params(rsi_period, macd_fast, macd_slow, bb_period, bb_std)
    result = technical.backtest(symbol, rsi_period, macd_fast, macd_slow, bb_period, bb_std)
    if result is None:
        raise _unavailable(symbol)
    return clean(result)


@router.get("/stocks/{symbol}/technical.csv")
def technical_csv(symbol: str, period: str = "1y", user: dict = Depends(current_user)):
    symbol = _symbol(symbol)
    csv = technical.export_csv(symbol, _period(period))
    if csv is None:
        raise _unavailable(symbol)
    name = f"{symbol}_technical_{file_stamp()}.csv"
    return Response(csv, media_type="text/csv", headers={"Content-Disposition": f'attachment; filename="{name}"'})


@router.get("/stocks/{symbol}/fundamentals")
def fundamental_analysis(symbol: str, user: dict = Depends(current_user)):
    symbol = _symbol(symbol)
    result = fundamentals.analyze(symbol)
    if result is None:
        raise _unavailable(symbol)
    return clean(result)


class PredictIn(BaseModel):
    period: Literal["1y", "2y", "5y"] = "2y"
    rf_estimators: int = Field(200, ge=50, le=300)
    rf_depth: int = Field(6, ge=2, le=12)
    test_size: int = Field(30, ge=20, le=40)
    use_chronos: bool = False


@router.post("/stocks/{symbol}/predict")
def predict(symbol: str, body: PredictIn, user: dict = Depends(current_user)):
    if not ML_AVAILABLE:
        raise HTTPException(503, "scikit-learn is not installed")
    symbol = _symbol(symbol)
    try:
        result = predictive.run(symbol, body.period, body.rf_estimators, body.rf_depth, body.test_size, body.use_chronos)
    except ValueError as e:
        raise HTTPException(400, str(e))
    if result is None:
        raise _unavailable(symbol)
    return clean(result)


class SentimentIn(BaseModel):
    days: Literal[7, 30] = 7
    source: Literal["finance", "news", "both"] = "both"


@router.get("/sentiment/account")
def sentiment_account(user: dict = Depends(current_user)):
    if not sentiment.status()["api_key"]:
        raise HTTPException(503, "SERP_API_KEY is not configured")
    try:
        return sentiment.account()
    except Exception as e:
        raise HTTPException(502, f"Could not reach SERPapi: {e}")


@router.post("/stocks/{symbol}/sentiment")
def sentiment_analysis(symbol: str, body: SentimentIn, user: dict = Depends(current_user)):
    try:
        return clean(sentiment.analyze(_symbol(symbol), body.days, body.source))
    except RuntimeError as e:
        raise HTTPException(503, str(e))


class AssessIn(BaseModel):
    period: str = "1y"
    include_sentiment: bool = True


@router.post("/stocks/{symbol}/assessment")
def assessment_context(symbol: str, body: AssessIn, user: dict = Depends(current_user)):
    try:
        ctx = assessment.build_context(user["username"], _symbol(symbol), _period(body.period), body.include_sentiment)
    except LookupError as e:
        raise HTTPException(502, str(e))
    return clean(ctx)


@router.post("/stocks/{symbol}/assessment/ai")
def assessment_ai(symbol: str, ctx: dict[str, Any] = Body(...), user: dict = Depends(current_user)):
    if ctx.get("symbol") != _symbol(symbol):
        raise HTTPException(400, "Context does not match symbol")
    try:
        return clean(assessment.generate(user["username"], ctx))
    except RuntimeError as e:
        raise HTTPException(503, str(e))
    except (KeyError, TypeError) as e:
        raise HTTPException(400, f"Malformed assessment context: {e}")


class EvaluateIn(BaseModel):
    context: dict[str, Any]
    ai: dict[str, Any]


@router.post("/stocks/{symbol}/assessment/evaluate")
def assessment_evaluate(symbol: str, body: EvaluateIn, user: dict = Depends(current_user)):
    if body.context.get("symbol") != _symbol(symbol):
        raise HTTPException(400, "Context does not match symbol")
    try:
        return clean(evaluation.evaluate(user["username"], body.context, body.ai))
    except RuntimeError as e:
        raise HTTPException(503, str(e))
    except (KeyError, TypeError, ValueError) as e:
        raise HTTPException(400, f"Malformed assessment: {e}")


class ReportIn(BaseModel):
    context: dict[str, Any]
    ai: dict[str, Any]
    evaluation: dict[str, Any] | None = None


@router.post("/reports/assessment.pdf")
def assessment_report(body: ReportIn, user: dict = Depends(current_user)):
    try:
        pdf = reports.assessment_pdf(body.context, body.ai, body.evaluation)
    except (KeyError, TypeError) as e:
        raise HTTPException(400, f"Malformed report payload: {e}")
    name = f"ai_report_{body.context.get('symbol', 'stock')}_{file_stamp()}.pdf"
    return Response(pdf, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="{name}"'})


@router.get("/track-record")
def get_track_record(user: dict = Depends(current_user)):
    return clean(track_record.build(user["username"]))
