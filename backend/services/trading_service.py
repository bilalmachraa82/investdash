"""Alpaca paper trading with safety rules and trade logging."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta

from loguru import logger

from backend.config import settings
from backend.database import get_trade_connection
from backend.exceptions import TradingError, TradingSafetyError
from backend.models.trading import TradePreview, TradeRequest, TradeResult
from backend.services.market_data_service import MarketDataService
from backend.services.portfolio_service import PortfolioService


class TradingService:
    def __init__(
        self,
        market_data: MarketDataService,
        portfolio: PortfolioService,
    ) -> None:
        if not settings.alpaca_api_key or not settings.alpaca_secret_key:
            raise TradingError("ALPACA_API_KEY and ALPACA_SECRET_KEY required")

        from alpaca.trading.client import TradingClient
        from alpaca.trading.enums import OrderSide, OrderType, TimeInForce
        from alpaca.trading.requests import (
            GetOrdersRequest,
            LimitOrderRequest,
            MarketOrderRequest,
            StopLimitOrderRequest,
            StopOrderRequest,
        )

        self._alpaca = TradingClient(
            api_key=settings.alpaca_api_key,
            secret_key=settings.alpaca_secret_key,
            paper=settings.alpaca_paper,
        )
        self._market = market_data
        self._portfolio = portfolio
        self._trade_db = get_trade_connection(settings.trade_db_path)

        # Store enums/requests for later use
        self._OrderSide = OrderSide
        self._OrderType = OrderType
        self._TimeInForce = TimeInForce
        self._MarketOrderRequest = MarketOrderRequest
        self._LimitOrderRequest = LimitOrderRequest
        self._StopOrderRequest = StopOrderRequest
        self._StopLimitOrderRequest = StopLimitOrderRequest
        self._GetOrdersRequest = GetOrdersRequest

    # ------------------------------------------------------------------
    # Safety checks
    # ------------------------------------------------------------------

    def _check_daily_limit(self) -> None:
        """Ensure we haven't exceeded the daily trade limit."""
        today = datetime.now().strftime("%Y-%m-%d")
        row = self._trade_db.execute(
            "SELECT COUNT(*) FROM trade_log WHERE timestamp >= ?",
            (today,),
        ).fetchone()
        if row and row[0] >= settings.daily_trade_limit:
            raise TradingSafetyError(
                f"Daily trade limit reached ({settings.daily_trade_limit}). Try again tomorrow."
            )

    async def _check_order_size(self, symbol: str, quantity: float, side: str) -> list[str]:
        """Check order size against portfolio limits. Returns warnings."""
        warnings: list[str] = []
        try:
            price = await self._market.get_current_price(symbol)
            order_value = price * quantity
            summary = await self._portfolio.get_summary()
            portfolio_value = summary.total_value

            if portfolio_value > 0:
                order_pct = order_value / portfolio_value
                if order_pct > settings.max_single_order_pct:
                    raise TradingSafetyError(
                        f"Order is {order_pct:.1%} of portfolio — exceeds "
                        f"{settings.max_single_order_pct:.0%} limit."
                    )

            if order_value > settings.max_single_order_usd:
                raise TradingSafetyError(
                    f"Order value ${order_value:,.2f} exceeds ${settings.max_single_order_usd:,.0f} limit."
                )

            if order_pct > 0.05:
                warnings.append(f"This trade is {order_pct:.1%} of your portfolio.")

        except (TradingSafetyError, TradingError):
            raise
        except Exception as e:
            warnings.append(f"Could not fully validate order size: {e}")

        return warnings

    # ------------------------------------------------------------------
    # Preview
    # ------------------------------------------------------------------

    async def preview_trade(self, request: TradeRequest) -> TradePreview:
        """Generate a preview of the trade with safety checks."""
        self._check_daily_limit()

        price = await self._market.get_current_price(request.symbol)
        estimated_total = price * request.quantity
        warnings = await self._check_order_size(request.symbol, request.quantity, request.side)

        try:
            summary = await self._portfolio.get_summary()
            portfolio_impact = (estimated_total / summary.total_value * 100) if summary.total_value > 0 else 0
        except Exception:
            portfolio_impact = 0

        if not request.paper:
            warnings.append("LIVE TRADING MODE — This will use real money!")

        return TradePreview(
            symbol=request.symbol.upper(),
            side=request.side,
            quantity=request.quantity,
            current_price=price,
            estimated_total=estimated_total,
            order_type=request.order_type,
            broker=request.broker,
            account_mode="paper" if request.paper else "live",
            portfolio_impact_pct=round(portfolio_impact, 2),
            warnings=warnings,
            requires_confirmation=settings.require_trade_confirmation,
        )

    # ------------------------------------------------------------------
    # Execute
    # ------------------------------------------------------------------

    async def execute_trade(self, request: TradeRequest) -> TradeResult:
        """Execute a trade via Alpaca after safety checks."""
        self._check_daily_limit()
        await self._check_order_size(request.symbol, request.quantity, request.side)

        side = self._OrderSide.BUY if request.side == "buy" else self._OrderSide.SELL
        tif_map = {"day": self._TimeInForce.DAY, "gtc": self._TimeInForce.GTC, "ioc": self._TimeInForce.IOC}
        tif = tif_map.get(request.time_in_force, self._TimeInForce.DAY)

        try:
            if request.order_type == "market":
                order_req = self._MarketOrderRequest(
                    symbol=request.symbol.upper(),
                    qty=request.quantity,
                    side=side,
                    time_in_force=tif,
                )
            elif request.order_type == "limit":
                if not request.limit_price:
                    raise TradingError("Limit price required for limit orders.")
                order_req = self._LimitOrderRequest(
                    symbol=request.symbol.upper(),
                    qty=request.quantity,
                    side=side,
                    time_in_force=tif,
                    limit_price=request.limit_price,
                )
            elif request.order_type == "stop":
                if not request.stop_price:
                    raise TradingError("Stop price required for stop orders.")
                order_req = self._StopOrderRequest(
                    symbol=request.symbol.upper(),
                    qty=request.quantity,
                    side=side,
                    time_in_force=tif,
                    stop_price=request.stop_price,
                )
            elif request.order_type == "stop_limit":
                if not request.limit_price or not request.stop_price:
                    raise TradingError("Both limit and stop prices required for stop-limit orders.")
                order_req = self._StopLimitOrderRequest(
                    symbol=request.symbol.upper(),
                    qty=request.quantity,
                    side=side,
                    time_in_force=tif,
                    limit_price=request.limit_price,
                    stop_price=request.stop_price,
                )
            else:
                raise TradingError(f"Unknown order type: {request.order_type}")

            order = self._alpaca.submit_order(order_req)

            status_map = {
                "new": "accepted",
                "accepted": "accepted",
                "filled": "filled",
                "partially_filled": "partial",
                "canceled": "cancelled",
                "rejected": "rejected",
            }
            result_status = status_map.get(str(order.status), "accepted")

            result = TradeResult(
                order_id=str(order.id),
                status=result_status,
                filled_quantity=float(order.filled_qty) if order.filled_qty else None,
                filled_price=float(order.filled_avg_price) if order.filled_avg_price else None,
                filled_at=order.filled_at,
                broker="alpaca",
                account_mode="paper" if request.paper else "live",
                message=f"Order {order.status} for {request.quantity} {request.symbol.upper()}",
            )

            self._log_trade(request, result)
            return result

        except (TradingError, TradingSafetyError):
            raise
        except Exception as e:
            logger.error("Alpaca trade error: {}", e)
            raise TradingError(f"Trade execution failed: {e}")

    # ------------------------------------------------------------------
    # Orders / Positions / Account
    # ------------------------------------------------------------------

    def get_open_orders(self) -> list[dict]:
        try:
            orders = self._alpaca.get_orders(
                filter=self._GetOrdersRequest(status="open")
            )
            return [
                {
                    "id": str(o.id),
                    "symbol": o.symbol,
                    "side": str(o.side),
                    "qty": str(o.qty),
                    "type": str(o.type),
                    "status": str(o.status),
                    "created_at": str(o.created_at),
                    "limit_price": str(o.limit_price) if o.limit_price else None,
                    "stop_price": str(o.stop_price) if o.stop_price else None,
                }
                for o in orders
            ]
        except Exception as e:
            raise TradingError(f"Failed to fetch orders: {e}")

    def cancel_order(self, order_id: str) -> dict:
        try:
            self._alpaca.cancel_order_by_id(order_id)
            return {"status": "cancelled", "order_id": order_id}
        except Exception as e:
            raise TradingError(f"Failed to cancel order: {e}")

    def get_positions(self) -> list[dict]:
        try:
            positions = self._alpaca.get_all_positions()
            return [
                {
                    "symbol": p.symbol,
                    "qty": str(p.qty),
                    "side": str(p.side),
                    "market_value": str(p.market_value),
                    "cost_basis": str(p.cost_basis),
                    "unrealized_pl": str(p.unrealized_pl),
                    "unrealized_plpc": str(p.unrealized_plpc),
                    "current_price": str(p.current_price),
                    "avg_entry_price": str(p.avg_entry_price),
                }
                for p in positions
            ]
        except Exception as e:
            raise TradingError(f"Failed to fetch positions: {e}")

    def get_account(self) -> dict:
        try:
            acct = self._alpaca.get_account()
            return {
                "id": str(acct.id),
                "status": str(acct.status),
                "cash": str(acct.cash),
                "portfolio_value": str(acct.portfolio_value),
                "buying_power": str(acct.buying_power),
                "equity": str(acct.equity),
                "currency": acct.currency,
                "pattern_day_trader": acct.pattern_day_trader,
                "trading_blocked": acct.trading_blocked,
                "account_blocked": acct.account_blocked,
            }
        except Exception as e:
            raise TradingError(f"Failed to fetch account: {e}")

    # ------------------------------------------------------------------
    # Trade log
    # ------------------------------------------------------------------

    def _log_trade(self, request: TradeRequest, result: TradeResult) -> None:
        if not settings.log_all_trades:
            return
        try:
            self._trade_db.execute(
                """INSERT INTO trade_log
                   (broker, account_mode, symbol, side, quantity, order_type,
                    limit_price, stop_price, status, order_id,
                    filled_price, filled_quantity)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    request.broker,
                    "paper" if request.paper else "live",
                    request.symbol.upper(),
                    request.side,
                    request.quantity,
                    request.order_type,
                    request.limit_price,
                    request.stop_price,
                    result.status,
                    result.order_id,
                    result.filled_price,
                    result.filled_quantity,
                ),
            )
            self._trade_db.commit()
        except Exception as e:
            logger.warning("Failed to log trade: {}", e)

    def get_trade_log(self, limit: int = 50) -> list[dict]:
        rows = self._trade_db.execute(
            """SELECT id, timestamp, broker, account_mode, symbol, side, quantity,
                      order_type, status, order_id, filled_price, filled_quantity, notes
               FROM trade_log ORDER BY timestamp DESC LIMIT ?""",
            (limit,),
        ).fetchall()
        cols = [
            "id", "timestamp", "broker", "account_mode", "symbol", "side",
            "quantity", "order_type", "status", "order_id", "filled_price",
            "filled_quantity", "notes",
        ]
        return [dict(zip(cols, row)) for row in rows]
