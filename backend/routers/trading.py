from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from backend.exceptions import TradingError, TradingSafetyError
from backend.models.trading import TradeRequest

router = APIRouter(prefix="/api/trading", tags=["trading"])


def _get_trading(request: Request):
    services = request.app.state.services
    trading = getattr(services, "trading", None)
    if trading is None:
        raise HTTPException(
            status_code=503,
            detail="Trading not available. Set ALPACA_API_KEY and ALPACA_SECRET_KEY.",
        )
    return trading


@router.get("/status")
async def trading_status(request: Request):
    trading = getattr(request.app.state.services, "trading", None)
    if trading is None:
        return {"status": "not_configured", "message": "Trading requires setup."}

    from backend.services.simulated_broker import SimulatedBroker

    broker_type = "simulator" if isinstance(trading, SimulatedBroker) else "alpaca"
    return {
        "status": "active",
        "broker": broker_type,
        "message": f"Paper trading ready ({broker_type}).",
    }


@router.post("/preview")
async def preview_trade(request: Request, body: TradeRequest):
    trading = _get_trading(request)
    try:
        preview = await trading.preview_trade(body)
        return preview.model_dump()
    except TradingSafetyError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except TradingError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/execute")
async def execute_trade(request: Request, body: TradeRequest):
    trading = _get_trading(request)
    try:
        result = await trading.execute_trade(body)
        return result.model_dump(mode="json")
    except TradingSafetyError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except TradingError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/orders")
async def get_orders(request: Request):
    trading = _get_trading(request)
    try:
        return trading.get_open_orders()
    except TradingError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/orders/{order_id}")
async def cancel_order(request: Request, order_id: str):
    trading = _get_trading(request)
    try:
        return trading.cancel_order(order_id)
    except TradingError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/positions")
async def get_positions(request: Request):
    trading = _get_trading(request)
    try:
        return trading.get_positions()
    except TradingError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/account")
async def get_account(request: Request):
    trading = _get_trading(request)
    try:
        return trading.get_account()
    except TradingError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/log")
async def get_trade_log(request: Request, limit: int = 50):
    trading = _get_trading(request)
    return trading.get_trade_log(limit)
