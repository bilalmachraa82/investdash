from __future__ import annotations

from fastapi import APIRouter, HTTPException, Path, Query, Request

from backend.exceptions import MarketDataError

router = APIRouter(prefix="/api/market", tags=["market"])


def _get_services(request: Request):
    return request.app.state.services


_TICKER = Path(description="Stock ticker symbol", pattern=r"^[A-Z0-9.\-\^]{1,10}$")


@router.get("/quote/{ticker}")
async def get_quote(request: Request, ticker: str = _TICKER):
    try:
        quote = await _get_services(request).market_data.get_quote(ticker)
        return quote.model_dump(mode="json")
    except MarketDataError as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/quotes")
async def get_quotes(request: Request, tickers: str = Query(..., description="Comma-separated tickers")):
    try:
        ticker_list = [t.strip() for t in tickers.split(",") if t.strip()]
        quotes = await _get_services(request).market_data.get_quotes(ticker_list)
        return [q.model_dump(mode="json") for q in quotes]
    except MarketDataError as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/history/{ticker}")
async def get_history(
    request: Request,
    ticker: str = _TICKER,
    period: str = "1y",
    interval: str = "1d",
):
    try:
        bars = await _get_services(request).market_data.get_history(ticker, period, interval)
        return [b.model_dump() for b in bars]
    except MarketDataError as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/fundamentals/{ticker}")
async def get_fundamentals(request: Request, ticker: str = _TICKER):
    try:
        data = await _get_services(request).market_data.get_fundamentals(ticker)
        return data.model_dump(mode="json")
    except MarketDataError as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/macro")
async def get_macro(request: Request):
    try:
        snapshot = await _get_services(request).market_data.get_macro_snapshot()
        return snapshot.model_dump(mode="json")
    except MarketDataError as e:
        raise HTTPException(status_code=502, detail=str(e))
