from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel


class TradeRequest(BaseModel):
    symbol: str
    side: Literal["buy", "sell"]
    quantity: float
    order_type: Literal["market", "limit", "stop", "stop_limit"] = "market"
    limit_price: Optional[float] = None
    stop_price: Optional[float] = None
    time_in_force: Literal["day", "gtc", "ioc"] = "day"
    broker: Literal["alpaca", "public"] = "alpaca"
    paper: bool = True


class TradePreview(BaseModel):
    symbol: str
    side: str
    quantity: float
    current_price: float
    estimated_total: float
    order_type: str
    broker: str
    account_mode: str
    portfolio_impact_pct: float
    warnings: list[str] = []
    requires_confirmation: bool = True


class TradeResult(BaseModel):
    order_id: str
    status: Literal["accepted", "filled", "partial", "rejected", "cancelled"]
    filled_quantity: Optional[float] = None
    filled_price: Optional[float] = None
    filled_at: Optional[datetime] = None
    broker: str
    account_mode: str
    message: str
