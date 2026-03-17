from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, computed_field


class Holding(BaseModel):
    ticker: str
    name: str
    quantity: float
    cost_basis_per_share: float
    current_price: float = 0.0
    asset_class: Literal["equity", "etf", "bond", "crypto", "reit", "option", "commodity"]
    sub_category: Optional[str] = None
    sector: Optional[str] = None
    account: str
    currency: str = "USD"
    added_date: str

    @computed_field
    @property
    def current_value(self) -> float:
        return self.quantity * self.current_price

    @computed_field
    @property
    def total_cost(self) -> float:
        return self.quantity * self.cost_basis_per_share

    @computed_field
    @property
    def gain_loss(self) -> float:
        return self.current_value - self.total_cost

    @computed_field
    @property
    def gain_loss_pct(self) -> float:
        if self.total_cost == 0:
            return 0.0
        return round((self.gain_loss / self.total_cost) * 100, 2)


class Portfolio(BaseModel):
    holdings: list[Holding]
    cash_positions: dict[str, float] = Field(default_factory=lambda: {"USD": 0})
    last_updated: datetime = Field(default_factory=datetime.now)
    source: Literal["manual", "plaid"] = "manual"


class PortfolioSummary(BaseModel):
    total_value: float
    total_cost: float
    total_gain_loss: float
    total_gain_loss_pct: float
    total_cash: float
    num_holdings: int
    top_holding_ticker: str
    top_holding_weight_pct: float
    sector_allocation: dict[str, float]
    asset_class_allocation: dict[str, float]
    account_allocation: dict[str, float]
    equity_pct: float
    crypto_pct: float
    gold_pct: float
    bond_pct: float
    reit_pct: float
