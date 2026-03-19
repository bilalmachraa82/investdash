"""Local paper trading simulator — no broker account needed.

Uses real market prices from yfinance. Tracks positions, orders,
and account balance in SQLite. Works from any country.
"""

from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime

from loguru import logger

from backend.config import settings
from backend.database import get_trade_connection
from backend.exceptions import TradingError, TradingSafetyError
from backend.models.trading import TradePreview, TradeRequest, TradeResult
from backend.services.market_data_service import MarketDataService
from backend.services.portfolio_service import PortfolioService

_INITIAL_CASH = 100_000.00  # $100k virtual cash


class SimulatedBroker:
    """Paper trading broker backed entirely by SQLite + yfinance prices."""

    def __init__(
        self,
        market_data: MarketDataService,
        portfolio: PortfolioService,
    ) -> None:
        self._market = market_data
        self._portfolio = portfolio
        self._db = get_trade_connection(settings.trade_db_path)
        self._ensure_sim_tables()
        logger.info("SimulatedBroker initialized (${:,.0f} starting cash)", _INITIAL_CASH)

    # ------------------------------------------------------------------
    # Schema
    # ------------------------------------------------------------------

    def _ensure_sim_tables(self) -> None:
        """Create simulator-specific tables if they don't exist."""
        self._db.execute("""
            CREATE TABLE IF NOT EXISTS sim_account (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                cash REAL NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)
        self._db.execute("""
            CREATE TABLE IF NOT EXISTS sim_positions (
                symbol TEXT PRIMARY KEY,
                qty REAL NOT NULL DEFAULT 0,
                avg_entry_price REAL NOT NULL DEFAULT 0,
                cost_basis REAL NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)
        self._db.execute("""
            CREATE TABLE IF NOT EXISTS sim_orders (
                id TEXT PRIMARY KEY,
                symbol TEXT NOT NULL,
                side TEXT NOT NULL,
                qty REAL NOT NULL,
                order_type TEXT NOT NULL,
                limit_price REAL,
                stop_price REAL,
                time_in_force TEXT NOT NULL DEFAULT 'day',
                status TEXT NOT NULL DEFAULT 'new',
                filled_price REAL,
                filled_qty REAL,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                filled_at TEXT
            )
        """)
        # Seed account if empty
        row = self._db.execute("SELECT cash FROM sim_account WHERE id = 1").fetchone()
        if row is None:
            self._db.execute(
                "INSERT INTO sim_account (id, cash) VALUES (1, ?)",
                (_INITIAL_CASH,),
            )
        self._db.commit()

    # ------------------------------------------------------------------
    # Account helpers
    # ------------------------------------------------------------------

    def _get_cash(self) -> float:
        row = self._db.execute("SELECT cash FROM sim_account WHERE id = 1").fetchone()
        return float(row[0]) if row else _INITIAL_CASH

    def _update_cash(self, delta: float) -> None:
        self._db.execute(
            "UPDATE sim_account SET cash = cash + ? WHERE id = 1",
            (delta,),
        )

    # ------------------------------------------------------------------
    # Safety checks
    # ------------------------------------------------------------------

    def _check_daily_limit(self) -> None:
        today = datetime.now().strftime("%Y-%m-%d")
        row = self._db.execute(
            "SELECT COUNT(*) FROM trade_log WHERE timestamp >= ?",
            (today,),
        ).fetchone()
        if row and row[0] >= settings.daily_trade_limit:
            raise TradingSafetyError(
                f"Daily trade limit reached ({settings.daily_trade_limit}). Try again tomorrow."
            )

    async def _check_order_size(self, symbol: str, quantity: float) -> list[str]:
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
                if order_pct > 0.05:
                    warnings.append(f"This trade is {order_pct:.1%} of your portfolio.")

            if order_value > settings.max_single_order_usd:
                raise TradingSafetyError(
                    f"Order value ${order_value:,.2f} exceeds "
                    f"${settings.max_single_order_usd:,.0f} limit."
                )
        except (TradingSafetyError, TradingError):
            raise
        except Exception as e:
            warnings.append(f"Could not fully validate order size: {e}")
        return warnings

    # ------------------------------------------------------------------
    # Preview
    # ------------------------------------------------------------------

    async def preview_trade(self, request: TradeRequest) -> TradePreview:
        self._check_daily_limit()

        price = await self._market.get_current_price(request.symbol)
        estimated_total = price * request.quantity
        warnings = await self._check_order_size(request.symbol, request.quantity)

        # Check sufficient cash for buys
        if request.side == "buy":
            cash = self._get_cash()
            if estimated_total > cash:
                warnings.append(
                    f"Insufficient cash: ${cash:,.2f} available, "
                    f"need ${estimated_total:,.2f}."
                )

        # Check sufficient shares for sells
        if request.side == "sell":
            pos = self._db.execute(
                "SELECT qty FROM sim_positions WHERE symbol = ?",
                (request.symbol.upper(),),
            ).fetchone()
            held = float(pos[0]) if pos else 0
            if request.quantity > held:
                warnings.append(
                    f"Insufficient shares: {held:g} held, "
                    f"trying to sell {request.quantity:g}."
                )

        try:
            summary = await self._portfolio.get_summary()
            impact = (estimated_total / summary.total_value * 100) if summary.total_value > 0 else 0
        except Exception:
            impact = 0

        return TradePreview(
            symbol=request.symbol.upper(),
            side=request.side,
            quantity=request.quantity,
            current_price=price,
            estimated_total=estimated_total,
            order_type=request.order_type,
            broker="simulator",
            account_mode="paper",
            portfolio_impact_pct=round(impact, 2),
            warnings=warnings,
            requires_confirmation=settings.require_trade_confirmation,
        )

    # ------------------------------------------------------------------
    # Execute
    # ------------------------------------------------------------------

    async def execute_trade(self, request: TradeRequest) -> TradeResult:
        self._check_daily_limit()
        await self._check_order_size(request.symbol, request.quantity)

        symbol = request.symbol.upper()
        price = await self._market.get_current_price(symbol)
        total = price * request.quantity
        order_id = str(uuid.uuid4())
        now = datetime.now()

        # Validate
        if request.side == "buy":
            cash = self._get_cash()
            if total > cash:
                raise TradingError(
                    f"Insufficient cash: ${cash:,.2f} available, "
                    f"need ${total:,.2f}."
                )
        elif request.side == "sell":
            pos = self._db.execute(
                "SELECT qty FROM sim_positions WHERE symbol = ?",
                (symbol,),
            ).fetchone()
            held = float(pos[0]) if pos else 0
            if request.quantity > held:
                raise TradingError(
                    f"Insufficient shares: {held:g} held, "
                    f"trying to sell {request.quantity:g}."
                )

        # Execute (market orders fill instantly at current price)
        if request.side == "buy":
            self._update_cash(-total)
            self._upsert_position(symbol, request.quantity, price)
        else:
            self._update_cash(+total)
            self._reduce_position(symbol, request.quantity)

        # Record order
        self._db.execute(
            """INSERT INTO sim_orders
               (id, symbol, side, qty, order_type, limit_price, stop_price,
                time_in_force, status, filled_price, filled_qty, filled_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'filled', ?, ?, ?)""",
            (
                order_id, symbol, request.side, request.quantity,
                request.order_type, request.limit_price, request.stop_price,
                request.time_in_force, price, request.quantity,
                now.isoformat(),
            ),
        )
        self._db.commit()

        result = TradeResult(
            order_id=order_id,
            status="filled",
            filled_quantity=request.quantity,
            filled_price=price,
            filled_at=now,
            broker="simulator",
            account_mode="paper",
            message=f"Simulated {request.side} of {request.quantity:g} {symbol} at ${price:,.2f}",
        )
        self._log_trade(request, result)
        return result

    # ------------------------------------------------------------------
    # Position management
    # ------------------------------------------------------------------

    def _upsert_position(self, symbol: str, qty: float, price: float) -> None:
        existing = self._db.execute(
            "SELECT qty, avg_entry_price, cost_basis FROM sim_positions WHERE symbol = ?",
            (symbol,),
        ).fetchone()

        if existing:
            old_qty, old_avg, old_cost = float(existing[0]), float(existing[1]), float(existing[2])
            new_qty = old_qty + qty
            new_cost = old_cost + (qty * price)
            new_avg = new_cost / new_qty if new_qty > 0 else 0
            self._db.execute(
                """UPDATE sim_positions
                   SET qty = ?, avg_entry_price = ?, cost_basis = ?, updated_at = datetime('now')
                   WHERE symbol = ?""",
                (new_qty, new_avg, new_cost, symbol),
            )
        else:
            self._db.execute(
                """INSERT INTO sim_positions (symbol, qty, avg_entry_price, cost_basis)
                   VALUES (?, ?, ?, ?)""",
                (symbol, qty, price, qty * price),
            )

    def _reduce_position(self, symbol: str, qty: float) -> None:
        existing = self._db.execute(
            "SELECT qty, avg_entry_price, cost_basis FROM sim_positions WHERE symbol = ?",
            (symbol,),
        ).fetchone()
        if not existing:
            return

        old_qty = float(existing[0])
        old_avg = float(existing[1])
        new_qty = old_qty - qty

        if new_qty <= 0.001:  # effectively zero
            self._db.execute("DELETE FROM sim_positions WHERE symbol = ?", (symbol,))
        else:
            new_cost = new_qty * old_avg
            self._db.execute(
                """UPDATE sim_positions
                   SET qty = ?, cost_basis = ?, updated_at = datetime('now')
                   WHERE symbol = ?""",
                (new_qty, new_cost, symbol),
            )

    # ------------------------------------------------------------------
    # Orders / Positions / Account
    # ------------------------------------------------------------------

    def get_open_orders(self) -> list[dict]:
        rows = self._db.execute(
            """SELECT id, symbol, side, qty, order_type, status, created_at,
                      limit_price, stop_price
               FROM sim_orders WHERE status IN ('new', 'accepted')
               ORDER BY created_at DESC"""
        ).fetchall()
        return [
            {
                "id": r[0], "symbol": r[1], "side": r[2], "qty": str(r[3]),
                "type": r[4], "status": r[5], "created_at": r[6],
                "limit_price": str(r[7]) if r[7] else None,
                "stop_price": str(r[8]) if r[8] else None,
            }
            for r in rows
        ]

    def cancel_order(self, order_id: str) -> dict:
        self._db.execute(
            "UPDATE sim_orders SET status = 'cancelled' WHERE id = ? AND status IN ('new', 'accepted')",
            (order_id,),
        )
        self._db.commit()
        return {"status": "cancelled", "order_id": order_id}

    def get_positions(self) -> list[dict]:
        rows = self._db.execute(
            "SELECT symbol, qty, avg_entry_price, cost_basis FROM sim_positions WHERE qty > 0.001"
        ).fetchall()
        positions = []
        for r in rows:
            symbol, qty, avg_price, cost_basis = r[0], float(r[1]), float(r[2]), float(r[3])
            # We can't call async from sync, so use cost_basis for now
            # Current price will be fetched by the UI
            market_value = qty * avg_price  # approximate
            unrealized_pl = 0.0
            positions.append({
                "symbol": symbol,
                "qty": str(qty),
                "side": "long",
                "market_value": str(market_value),
                "cost_basis": str(cost_basis),
                "unrealized_pl": str(unrealized_pl),
                "unrealized_plpc": "0",
                "current_price": str(avg_price),
                "avg_entry_price": str(avg_price),
            })
        return positions

    async def get_positions_with_prices(self) -> list[dict]:
        """Positions with live market prices."""
        rows = self._db.execute(
            "SELECT symbol, qty, avg_entry_price, cost_basis FROM sim_positions WHERE qty > 0.001"
        ).fetchall()
        positions = []
        for r in rows:
            symbol, qty, avg_price, cost_basis = r[0], float(r[1]), float(r[2]), float(r[3])
            try:
                current_price = await self._market.get_current_price(symbol)
            except Exception:
                current_price = avg_price
            market_value = qty * current_price
            unrealized_pl = market_value - cost_basis
            unrealized_plpc = unrealized_pl / cost_basis if cost_basis > 0 else 0
            positions.append({
                "symbol": symbol,
                "qty": str(qty),
                "side": "long",
                "market_value": str(round(market_value, 2)),
                "cost_basis": str(round(cost_basis, 2)),
                "unrealized_pl": str(round(unrealized_pl, 2)),
                "unrealized_plpc": str(round(unrealized_plpc, 4)),
                "current_price": str(round(current_price, 2)),
                "avg_entry_price": str(round(avg_price, 2)),
            })
        return positions

    def get_account(self) -> dict:
        cash = self._get_cash()
        rows = self._db.execute(
            "SELECT qty, avg_entry_price FROM sim_positions WHERE qty > 0.001"
        ).fetchall()
        positions_value = sum(float(r[0]) * float(r[1]) for r in rows)
        equity = cash + positions_value
        return {
            "id": "sim-local",
            "status": "ACTIVE",
            "cash": str(round(cash, 2)),
            "portfolio_value": str(round(equity, 2)),
            "buying_power": str(round(cash, 2)),
            "equity": str(round(equity, 2)),
            "currency": "USD",
            "pattern_day_trader": False,
            "trading_blocked": False,
            "account_blocked": False,
        }

    # ------------------------------------------------------------------
    # Trade log (reuses existing trade_log table)
    # ------------------------------------------------------------------

    def _log_trade(self, request: TradeRequest, result: TradeResult) -> None:
        if not settings.log_all_trades:
            return
        try:
            self._db.execute(
                """INSERT INTO trade_log
                   (broker, account_mode, symbol, side, quantity, order_type,
                    limit_price, stop_price, status, order_id,
                    filled_price, filled_quantity)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    "simulator",
                    "paper",
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
            self._db.commit()
        except Exception as e:
            logger.warning("Failed to log simulated trade: {}", e)

    def get_trade_log(self, limit: int = 50) -> list[dict]:
        rows = self._db.execute(
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
