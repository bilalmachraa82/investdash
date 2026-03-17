from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Optional

from loguru import logger

from backend.config import settings
from backend.exceptions import PortfolioError
from backend.models.portfolio import Holding, Portfolio, PortfolioSummary
from backend.services.market_data_service import MarketDataService


class PortfolioService:
    def __init__(
        self,
        market_data: MarketDataService,
        portfolio_path: Optional[Path] = None,
    ) -> None:
        self._market = market_data
        self._path = portfolio_path or settings.portfolio_path

    def _load_raw(self) -> dict:
        try:
            with open(self._path, "r") as f:
                return json.load(f)
        except FileNotFoundError:
            raise PortfolioError(f"Portfolio file not found: {self._path}")
        except json.JSONDecodeError as e:
            raise PortfolioError(f"Invalid portfolio JSON: {e}")

    def _save_raw(self, data: dict) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._path, "w") as f:
            json.dump(data, f, indent=2, default=str)

    async def get_portfolio(self) -> Portfolio:
        raw = self._load_raw()
        holdings_raw = raw.get("holdings", [])
        cash = raw.get("cash_positions", {"USD": 0})

        holdings = [Holding(**h) for h in holdings_raw]

        # Enrich with live prices
        tickers = [h.ticker for h in holdings]
        quotes = await self._market.get_quotes(tickers)
        price_map = {q.ticker: q.price for q in quotes}

        for h in holdings:
            h.current_price = price_map.get(h.ticker.upper(), 0.0)

        return Portfolio(holdings=holdings, cash_positions=cash)

    async def get_summary(self) -> PortfolioSummary:
        portfolio = await self.get_portfolio()
        holdings = portfolio.holdings

        if not holdings:
            raise PortfolioError("Portfolio has no holdings")

        total_value = sum(h.current_value for h in holdings)
        total_cost = sum(h.total_cost for h in holdings)
        total_cash = sum(portfolio.cash_positions.values())

        grand_total = total_value + total_cash
        total_gl = total_value - total_cost
        total_gl_pct = round((total_gl / total_cost * 100), 2) if total_cost else 0.0

        # Sector allocation
        sector_alloc: dict[str, float] = {}
        asset_class_alloc: dict[str, float] = {}
        account_alloc: dict[str, float] = {}

        for h in holdings:
            key_sector = h.sector or "Unknown"
            sector_alloc[key_sector] = sector_alloc.get(key_sector, 0) + h.current_value

            asset_class_alloc[h.asset_class] = (
                asset_class_alloc.get(h.asset_class, 0) + h.current_value
            )

            account_alloc[h.account] = (
                account_alloc.get(h.account, 0) + h.current_value
            )

        # Convert to percentages
        if grand_total > 0:
            sector_alloc = {
                k: round(v / grand_total * 100, 2) for k, v in sector_alloc.items()
            }
            asset_class_alloc = {
                k: round(v / grand_total * 100, 2)
                for k, v in asset_class_alloc.items()
            }
            account_alloc = {
                k: round(v / grand_total * 100, 2) for k, v in account_alloc.items()
            }

        # Top holding
        sorted_h = sorted(holdings, key=lambda x: x.current_value, reverse=True)
        top = sorted_h[0]
        top_weight = round(top.current_value / grand_total * 100, 2) if grand_total else 0

        # Asset class exposure percentages
        def _pct(ac: str) -> float:
            val = sum(h.current_value for h in holdings if h.asset_class == ac)
            return round(val / grand_total * 100, 2) if grand_total else 0.0

        return PortfolioSummary(
            total_value=round(grand_total, 2),
            total_cost=round(total_cost, 2),
            total_gain_loss=round(total_gl, 2),
            total_gain_loss_pct=total_gl_pct,
            total_cash=round(total_cash, 2),
            num_holdings=len(holdings),
            top_holding_ticker=top.ticker,
            top_holding_weight_pct=top_weight,
            sector_allocation=sector_alloc,
            asset_class_allocation=asset_class_alloc,
            account_allocation=account_alloc,
            equity_pct=_pct("equity"),
            crypto_pct=_pct("crypto"),
            gold_pct=_pct("commodity"),
            bond_pct=_pct("bond"),
            reit_pct=_pct("reit"),
        )

    async def get_holding_detail(self, ticker: str) -> Optional[Holding]:
        portfolio = await self.get_portfolio()
        for h in portfolio.holdings:
            if h.ticker.upper() == ticker.upper():
                return h
        return None

    # ── CRUD ────────────────────────────────────────────────────

    def add_holding(self, holding: Holding) -> None:
        raw = self._load_raw()
        raw.setdefault("holdings", []).append(
            holding.model_dump(exclude={"current_value", "total_cost", "gain_loss", "gain_loss_pct"})
        )
        self._save_raw(raw)
        logger.info("Added holding: {}", holding.ticker)

    def remove_holding(self, ticker: str) -> bool:
        raw = self._load_raw()
        original = len(raw.get("holdings", []))
        raw["holdings"] = [
            h for h in raw.get("holdings", []) if h["ticker"].upper() != ticker.upper()
        ]
        if len(raw["holdings"]) < original:
            self._save_raw(raw)
            logger.info("Removed holding: {}", ticker)
            return True
        return False

    def update_cash(self, currency: str, amount: float) -> None:
        raw = self._load_raw()
        raw.setdefault("cash_positions", {})[currency] = amount
        self._save_raw(raw)
        logger.info("Updated cash {}: {}", currency, amount)
