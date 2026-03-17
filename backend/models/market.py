from datetime import datetime
from typing import Optional

from pydantic import BaseModel, computed_field


class StockQuote(BaseModel):
    ticker: str
    price: float
    change: float
    change_pct: float
    volume: int = 0
    market_cap: Optional[float] = None
    pe_ratio: Optional[float] = None
    forward_pe: Optional[float] = None
    dividend_yield: Optional[float] = None
    beta: Optional[float] = None
    fifty_two_week_high: float = 0.0
    fifty_two_week_low: float = 0.0
    sector: Optional[str] = None
    industry: Optional[str] = None
    timestamp: datetime


class StockFundamentals(BaseModel):
    ticker: str
    name: str
    sector: Optional[str] = None
    industry: Optional[str] = None
    market_cap: Optional[float] = None
    pe_ratio: Optional[float] = None
    forward_pe: Optional[float] = None
    peg_ratio: Optional[float] = None
    price_to_book: Optional[float] = None
    price_to_sales: Optional[float] = None
    ev_to_ebitda: Optional[float] = None
    profit_margin: Optional[float] = None
    operating_margin: Optional[float] = None
    roe: Optional[float] = None
    roa: Optional[float] = None
    revenue: Optional[float] = None
    revenue_growth: Optional[float] = None
    earnings_growth: Optional[float] = None
    debt_to_equity: Optional[float] = None
    current_ratio: Optional[float] = None
    free_cash_flow: Optional[float] = None
    dividend_yield: Optional[float] = None
    payout_ratio: Optional[float] = None
    analyst_target_mean: Optional[float] = None
    analyst_recommendation: Optional[str] = None


class MacroSnapshot(BaseModel):
    fed_funds_rate: Optional[float] = None
    treasury_2y: Optional[float] = None
    treasury_10y: Optional[float] = None
    treasury_30y: Optional[float] = None
    yield_curve_spread: Optional[float] = None
    cpi_yoy: Optional[float] = None
    unemployment_rate: Optional[float] = None
    gold_spot_usd: Optional[float] = None
    timestamp: datetime

    @computed_field
    @property
    def yield_curve_inverted(self) -> bool:
        if self.yield_curve_spread is None:
            return False
        return self.yield_curve_spread < 0


class HistoricalBar(BaseModel):
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: int = 0


class DeFiYield(BaseModel):
    protocol: str
    chain: str
    pool: str
    apy: float
    tvl_usd: float
    stablecoin: bool = False
