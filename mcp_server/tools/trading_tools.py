"""MCP tools for Alpaca paper trading."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from backend.services import ServiceContainer


def register_trading_tools(mcp: FastMCP, services: ServiceContainer) -> None:
    """Register trading tools with the MCP server (only if trading is available)."""

    if services.trading is None:
        return

    trading = services.trading

    @mcp.tool()
    async def preview_trade(
        symbol: str,
        side: str,
        quantity: float,
        order_type: str = "market",
        limit_price: float | None = None,
        stop_price: float | None = None,
    ) -> dict:
        """Preview a trade before executing it. Shows estimated cost, portfolio impact, and safety warnings.

        Args:
            symbol: Stock ticker (e.g. AAPL, MSFT)
            side: 'buy' or 'sell'
            quantity: Number of shares
            order_type: 'market', 'limit', 'stop', or 'stop_limit'
            limit_price: Required for limit and stop_limit orders
            stop_price: Required for stop and stop_limit orders
        """
        from backend.models.trading import TradeRequest

        request = TradeRequest(
            symbol=symbol.upper(),
            side=side,
            quantity=quantity,
            order_type=order_type,
            limit_price=limit_price,
            stop_price=stop_price,
        )
        preview = await trading.preview_trade(request)
        return preview.model_dump()

    @mcp.tool()
    async def execute_trade(
        symbol: str,
        side: str,
        quantity: float,
        order_type: str = "market",
        limit_price: float | None = None,
        stop_price: float | None = None,
        time_in_force: str = "day",
    ) -> dict:
        """Execute a paper trade via Alpaca. Always preview first before executing.

        Args:
            symbol: Stock ticker (e.g. AAPL, MSFT)
            side: 'buy' or 'sell'
            quantity: Number of shares
            order_type: 'market', 'limit', 'stop', or 'stop_limit'
            limit_price: Required for limit and stop_limit orders
            stop_price: Required for stop and stop_limit orders
            time_in_force: 'day', 'gtc', or 'ioc'
        """
        from backend.models.trading import TradeRequest

        request = TradeRequest(
            symbol=symbol.upper(),
            side=side,
            quantity=quantity,
            order_type=order_type,
            limit_price=limit_price,
            stop_price=stop_price,
            time_in_force=time_in_force,
        )
        result = await trading.execute_trade(request)
        return result.model_dump(mode="json")

    @mcp.tool()
    def open_orders() -> list[dict]:
        """Get all currently open orders in the Alpaca paper trading account."""
        return trading.get_open_orders()

    @mcp.tool()
    def trade_history(limit: int = 20) -> list[dict]:
        """Get recent trade history from the local trade log.

        Args:
            limit: Maximum number of trades to return (default 20)
        """
        return trading.get_trade_log(limit)

    @mcp.tool()
    def trading_account() -> dict:
        """Get the Alpaca paper trading account details including cash, equity, and buying power."""
        return trading.get_account()
