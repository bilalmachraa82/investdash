from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.services.cache_service import CacheService
    from backend.services.market_data_service import MarketDataService
    from backend.services.portfolio_service import PortfolioService
    from backend.services.trading_service import TradingService


@dataclass
class ServiceContainer:
    cache: "CacheService" = field(default=None)  # type: ignore[assignment]
    market_data: "MarketDataService" = field(default=None)  # type: ignore[assignment]
    portfolio: "PortfolioService" = field(default=None)  # type: ignore[assignment]
    trading: "TradingService | None" = None
