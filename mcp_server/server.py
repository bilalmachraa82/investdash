from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from backend.config import settings
from backend.services import ServiceContainer
from backend.services.cache_service import CacheService
from backend.services.market_data_service import MarketDataService
from backend.services.portfolio_service import PortfolioService
from mcp_server.tools.analysis_tools import register_analysis_tools
from mcp_server.tools.market_tools import register_market_tools
from mcp_server.tools.portfolio_tools import register_portfolio_tools
from mcp_server.tools.trading_tools import register_trading_tools

mcp = FastMCP(
    "InvestDash",
    instructions="AI-powered personal investment dashboard — portfolio tracking, market data, and analysis",
)

# Build services
_cache = CacheService(settings.cache_db_path)
_market = MarketDataService(_cache)
_portfolio = PortfolioService(_market)

services = ServiceContainer(
    cache=_cache,
    market_data=_market,
    portfolio=_portfolio,
)

# Optionally build trading service
if settings.alpaca_api_key and settings.alpaca_secret_key:
    try:
        from backend.services.trading_service import TradingService

        services.trading = TradingService(_market, _portfolio)
    except Exception:
        pass  # trading will remain None

# Register tools
register_portfolio_tools(mcp, services)
register_market_tools(mcp, services)
register_analysis_tools(mcp, services)
register_trading_tools(mcp, services)


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
