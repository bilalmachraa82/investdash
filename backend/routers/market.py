from __future__ import annotations

import re

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request
from loguru import logger

from backend.exceptions import MarketDataError
from backend.middleware import verify_api_key

router = APIRouter(
    prefix="/api/market",
    tags=["market"],
    dependencies=[Depends(verify_api_key)],
)


def _get_services(request: Request):
    return request.app.state.services


_TICKER = Path(description="Stock ticker symbol", pattern=r"^[A-Z0-9.\-\^]{1,10}$")
_TICKER_PATTERN = re.compile(r"^[A-Z0-9.\-\^]{1,10}$")
_MAX_BATCH_TICKERS = 50

_VALID_PERIODS = {
    "1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max",
}
_VALID_INTERVALS = {
    "1m", "2m", "5m", "15m", "30m", "60m", "90m", "1h", "1d", "5d", "1wk", "1mo", "3mo",
}


@router.get("/quote/{ticker}")
async def get_quote(request: Request, ticker: str = _TICKER):
    try:
        quote = await _get_services(request).market_data.get_quote(ticker)
        return quote.model_dump(mode="json")
    except MarketDataError:
        raise HTTPException(status_code=502, detail="Failed to fetch quote.")


@router.get("/quotes")
async def get_quotes(
    request: Request,
    tickers: str = Query(..., description="Comma-separated tickers", max_length=2000),
):
    raw = [t.strip().upper() for t in tickers.split(",") if t.strip()]
    if not raw:
        raise HTTPException(status_code=400, detail="No tickers provided.")
    if len(raw) > _MAX_BATCH_TICKERS:
        raise HTTPException(
            status_code=400,
            detail=f"Too many tickers (max {_MAX_BATCH_TICKERS}).",
        )
    invalid = [t for t in raw if not _TICKER_PATTERN.match(t)]
    if invalid:
        raise HTTPException(status_code=400, detail="Invalid ticker format.")
    try:
        quotes = await _get_services(request).market_data.get_quotes(raw)
        return [q.model_dump(mode="json") for q in quotes]
    except MarketDataError:
        raise HTTPException(status_code=502, detail="Failed to fetch quotes.")


@router.get("/history/{ticker}")
async def get_history(
    request: Request,
    ticker: str = _TICKER,
    period: str = Query(default="1y"),
    interval: str = Query(default="1d"),
):
    if period not in _VALID_PERIODS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid period. Allowed: {sorted(_VALID_PERIODS)}",
        )
    if interval not in _VALID_INTERVALS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid interval. Allowed: {sorted(_VALID_INTERVALS)}",
        )
    try:
        bars = await _get_services(request).market_data.get_history(ticker, period, interval)
        return [b.model_dump() for b in bars]
    except MarketDataError:
        raise HTTPException(status_code=502, detail="Failed to fetch history.")


@router.get("/fundamentals/{ticker}")
async def get_fundamentals(request: Request, ticker: str = _TICKER):
    try:
        data = await _get_services(request).market_data.get_fundamentals(ticker)
        return data.model_dump(mode="json")
    except MarketDataError:
        raise HTTPException(status_code=502, detail="Failed to fetch fundamentals.")


@router.get("/macro")
async def get_macro(request: Request):
    try:
        snapshot = await _get_services(request).market_data.get_macro_snapshot()
        return snapshot.model_dump(mode="json")
    except MarketDataError:
        raise HTTPException(status_code=502, detail="Failed to fetch macro data.")
