from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from backend.exceptions import PortfolioError

router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])


def _get_services(request: Request):
    return request.app.state.services


@router.get("/summary")
async def get_summary(request: Request):
    try:
        return (await _get_services(request).portfolio.get_summary()).model_dump()
    except PortfolioError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/holdings")
async def get_holdings(request: Request):
    try:
        portfolio = await _get_services(request).portfolio.get_portfolio()
        return {
            "holdings": [h.model_dump() for h in portfolio.holdings],
            "cash_positions": portfolio.cash_positions,
        }
    except PortfolioError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/allocation/{allocation_type}")
async def get_allocation(request: Request, allocation_type: str):
    try:
        summary = await _get_services(request).portfolio.get_summary()
        alloc_map = {
            "asset_class": summary.asset_class_allocation,
            "sector": summary.sector_allocation,
            "account": summary.account_allocation,
        }
        alloc = alloc_map.get(allocation_type)
        if alloc is None:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid type: {allocation_type}. Use 'asset_class', 'sector', or 'account'.",
            )
        return {"type": allocation_type, "allocation": alloc}
    except PortfolioError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/holding/{ticker}")
async def get_holding(request: Request, ticker: str):
    holding = await _get_services(request).portfolio.get_holding_detail(ticker)
    if holding is None:
        raise HTTPException(status_code=404, detail=f"{ticker} not found in portfolio")
    return holding.model_dump()
