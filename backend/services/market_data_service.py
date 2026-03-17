from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from functools import partial
from typing import Optional

import yfinance as yf
from loguru import logger

from backend.config import settings
from backend.exceptions import MarketDataError
from backend.models.market import (
    DeFiYield,
    HistoricalBar,
    MacroSnapshot,
    StockFundamentals,
    StockQuote,
)
from backend.services.cache_service import CacheService

_executor = ThreadPoolExecutor(max_workers=4)


def _run_sync(func, *args, **kwargs):
    """Run a sync function in thread pool, return awaitable."""
    loop = asyncio.get_event_loop()
    return loop.run_in_executor(_executor, partial(func, *args, **kwargs))


class MarketDataService:
    def __init__(self, cache: CacheService) -> None:
        self._cache = cache

    # ── Quotes ──────────────────────────────────────────────────

    def _fetch_quote_sync(self, ticker: str) -> StockQuote:
        t = yf.Ticker(ticker)
        info = t.info or {}
        price = info.get("currentPrice") or info.get("regularMarketPrice") or 0.0
        prev = info.get("previousClose") or info.get("regularMarketPreviousClose") or price
        change = price - prev
        change_pct = (change / prev * 100) if prev else 0.0

        return StockQuote(
            ticker=ticker.upper(),
            price=round(price, 4),
            change=round(change, 4),
            change_pct=round(change_pct, 2),
            volume=info.get("volume") or info.get("regularMarketVolume") or 0,
            market_cap=info.get("marketCap"),
            pe_ratio=info.get("trailingPE"),
            forward_pe=info.get("forwardPE"),
            dividend_yield=info.get("dividendYield"),
            beta=info.get("beta"),
            fifty_two_week_high=info.get("fiftyTwoWeekHigh") or 0.0,
            fifty_two_week_low=info.get("fiftyTwoWeekLow") or 0.0,
            sector=info.get("sector"),
            industry=info.get("industry"),
            timestamp=datetime.now(timezone.utc),
        )

    async def get_quote(self, ticker: str) -> StockQuote:
        cache_key = f"quote:{ticker.upper()}"
        is_crypto = ticker.upper().endswith("-USD")
        ttl = settings.cache_ttl_crypto if is_crypto else settings.cache_ttl_quote

        cached = self._cache.get(cache_key)
        if cached:
            return StockQuote(**cached)

        try:
            quote = await _run_sync(self._fetch_quote_sync, ticker)
            self._cache.set(cache_key, quote.model_dump(mode="json"), ttl)
            return quote
        except Exception as e:
            logger.warning("yfinance quote failed for {}: {}", ticker, e)
            stale = self._cache.get_stale(cache_key)
            if stale:
                logger.info("Returning stale cache for {}", ticker)
                return StockQuote(**stale)
            raise MarketDataError(f"Failed to get quote for {ticker}: {e}") from e

    async def get_quotes(self, tickers: list[str]) -> list[StockQuote]:
        tasks = [self.get_quote(t) for t in tickers]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        quotes = []
        for r in results:
            if isinstance(r, StockQuote):
                quotes.append(r)
            else:
                logger.warning("Quote failed: {}", r)
        return quotes

    # ── History ─────────────────────────────────────────────────

    def _fetch_history_sync(
        self, ticker: str, period: str, interval: str
    ) -> list[HistoricalBar]:
        t = yf.Ticker(ticker)
        df = t.history(period=period, interval=interval)
        if df.empty:
            return []
        bars = []
        for idx, row in df.iterrows():
            bars.append(
                HistoricalBar(
                    date=idx.strftime("%Y-%m-%d"),
                    open=round(row["Open"], 4),
                    high=round(row["High"], 4),
                    low=round(row["Low"], 4),
                    close=round(row["Close"], 4),
                    volume=int(row.get("Volume", 0)),
                )
            )
        return bars

    async def get_history(
        self,
        ticker: str,
        period: str = "1y",
        interval: str = "1d",
    ) -> list[HistoricalBar]:
        cache_key = f"history:{ticker.upper()}:{period}:{interval}"

        cached = self._cache.get(cache_key)
        if cached:
            return [HistoricalBar(**b) for b in cached]

        try:
            bars = await _run_sync(self._fetch_history_sync, ticker, period, interval)
            self._cache.set(
                cache_key,
                [b.model_dump() for b in bars],
                settings.cache_ttl_historical,
            )
            return bars
        except Exception as e:
            logger.warning("yfinance history failed for {}: {}", ticker, e)
            stale = self._cache.get_stale(cache_key)
            if stale:
                return [HistoricalBar(**b) for b in stale]
            raise MarketDataError(f"Failed to get history for {ticker}: {e}") from e

    # ── Fundamentals ────────────────────────────────────────────

    def _fetch_fundamentals_sync(self, ticker: str) -> StockFundamentals:
        t = yf.Ticker(ticker)
        info = t.info or {}
        return StockFundamentals(
            ticker=ticker.upper(),
            name=info.get("longName") or info.get("shortName") or ticker,
            sector=info.get("sector"),
            industry=info.get("industry"),
            market_cap=info.get("marketCap"),
            pe_ratio=info.get("trailingPE"),
            forward_pe=info.get("forwardPE"),
            peg_ratio=info.get("pegRatio"),
            price_to_book=info.get("priceToBook"),
            price_to_sales=info.get("priceToSalesTrailing12Months"),
            ev_to_ebitda=info.get("enterpriseToEbitda"),
            profit_margin=info.get("profitMargins"),
            operating_margin=info.get("operatingMargins"),
            roe=info.get("returnOnEquity"),
            roa=info.get("returnOnAssets"),
            revenue=info.get("totalRevenue"),
            revenue_growth=info.get("revenueGrowth"),
            earnings_growth=info.get("earningsGrowth"),
            debt_to_equity=info.get("debtToEquity"),
            current_ratio=info.get("currentRatio"),
            free_cash_flow=info.get("freeCashflow"),
            dividend_yield=info.get("dividendYield"),
            payout_ratio=info.get("payoutRatio"),
            analyst_target_mean=info.get("targetMeanPrice"),
            analyst_recommendation=info.get("recommendationKey"),
        )

    async def get_fundamentals(self, ticker: str) -> StockFundamentals:
        cache_key = f"fundamentals:{ticker.upper()}"

        cached = self._cache.get(cache_key)
        if cached:
            return StockFundamentals(**cached)

        try:
            data = await _run_sync(self._fetch_fundamentals_sync, ticker)
            self._cache.set(
                cache_key, data.model_dump(mode="json"), settings.cache_ttl_fundamentals
            )
            return data
        except Exception as e:
            logger.warning("yfinance fundamentals failed for {}: {}", ticker, e)
            stale = self._cache.get_stale(cache_key)
            if stale:
                return StockFundamentals(**stale)
            raise MarketDataError(
                f"Failed to get fundamentals for {ticker}: {e}"
            ) from e

    # ── Macro Snapshot ──────────────────────────────────────────

    def _fetch_macro_sync(self) -> MacroSnapshot:
        data: dict = {}
        try:
            tnx = yf.Ticker("^TNX").info or {}
            data["treasury_10y"] = tnx.get("regularMarketPrice")
        except Exception:
            pass
        try:
            tyx = yf.Ticker("^TYX").info or {}
            data["treasury_30y"] = tyx.get("regularMarketPrice")
        except Exception:
            pass
        try:
            two = yf.Ticker("2YY=F").info or {}
            data["treasury_2y"] = two.get("regularMarketPrice")
        except Exception:
            pass
        if data.get("treasury_2y") and data.get("treasury_10y"):
            data["yield_curve_spread"] = round(
                data["treasury_10y"] - data["treasury_2y"], 3
            )
        try:
            gold = yf.Ticker("GC=F").info or {}
            data["gold_spot_usd"] = gold.get("regularMarketPrice")
        except Exception:
            pass
        return MacroSnapshot(timestamp=datetime.now(timezone.utc), **data)

    async def get_macro_snapshot(self) -> MacroSnapshot:
        cache_key = "macro:snapshot"

        cached = self._cache.get(cache_key)
        if cached:
            return MacroSnapshot(**cached)

        try:
            snapshot = await _run_sync(self._fetch_macro_sync)
            self._cache.set(
                cache_key, snapshot.model_dump(mode="json"), settings.cache_ttl_macro
            )
            return snapshot
        except Exception as e:
            logger.warning("Macro snapshot failed: {}", e)
            stale = self._cache.get_stale(cache_key)
            if stale:
                return MacroSnapshot(**stale)
            raise MarketDataError(f"Failed to get macro snapshot: {e}") from e

    # ── Helpers ─────────────────────────────────────────────────

    async def get_current_price(self, ticker: str) -> float:
        quote = await self.get_quote(ticker)
        return quote.price
