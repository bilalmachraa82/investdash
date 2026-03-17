"""HTTP client for the InvestDash FastAPI backend — used by Streamlit."""

from __future__ import annotations

from typing import Iterator

import httpx

from backend.config import settings


class InvestDashClient:
    def __init__(self, base_url: str | None = None) -> None:
        url = base_url or f"http://{settings.api_host}:{settings.api_port}"
        self._client = httpx.Client(base_url=url, timeout=30.0)

    # ------------------------------------------------------------------
    # Portfolio
    # ------------------------------------------------------------------

    def get_portfolio_summary(self) -> dict:
        r = self._client.get("/api/portfolio/summary")
        r.raise_for_status()
        return r.json()

    def get_holdings(self) -> dict:
        r = self._client.get("/api/portfolio/holdings")
        r.raise_for_status()
        return r.json()

    def get_allocation(self, allocation_type: str) -> dict:
        r = self._client.get(f"/api/portfolio/allocation/{allocation_type}")
        r.raise_for_status()
        return r.json()

    def get_holding_detail(self, ticker: str) -> dict:
        r = self._client.get(f"/api/portfolio/holding/{ticker}")
        r.raise_for_status()
        return r.json()

    # ------------------------------------------------------------------
    # Market
    # ------------------------------------------------------------------

    def get_quote(self, ticker: str) -> dict:
        r = self._client.get(f"/api/market/quote/{ticker}")
        r.raise_for_status()
        return r.json()

    def get_quotes(self, tickers: list[str]) -> list[dict]:
        r = self._client.get("/api/market/quotes", params={"tickers": ",".join(tickers)})
        r.raise_for_status()
        return r.json()

    def get_history(self, ticker: str, period: str = "1y", interval: str = "1d") -> list[dict]:
        r = self._client.get(
            f"/api/market/history/{ticker}",
            params={"period": period, "interval": interval},
        )
        r.raise_for_status()
        return r.json()

    def get_fundamentals(self, ticker: str) -> dict:
        r = self._client.get(f"/api/market/fundamentals/{ticker}")
        r.raise_for_status()
        return r.json()

    def get_macro(self) -> dict:
        r = self._client.get("/api/market/macro")
        r.raise_for_status()
        return r.json()

    # ------------------------------------------------------------------
    # Chat (SSE streaming)
    # ------------------------------------------------------------------

    def chat_stream(self, message: str, conversation_id: str | None = None) -> Iterator[dict]:
        """Stream chat responses via SSE. Yields dicts with 'content', 'done', or 'error'."""
        import json

        payload = {"message": message}
        if conversation_id:
            payload["conversation_id"] = conversation_id

        with self._client.stream("POST", "/api/chat", json=payload) as response:
            response.raise_for_status()
            for line in response.iter_lines():
                if line.startswith("data: "):
                    try:
                        yield json.loads(line[6:])
                    except json.JSONDecodeError:
                        continue

    # ------------------------------------------------------------------
    # Trading
    # ------------------------------------------------------------------

    def get_trading_status(self) -> dict:
        r = self._client.get("/api/trading/status")
        r.raise_for_status()
        return r.json()

    def preview_trade(self, trade: dict) -> dict:
        r = self._client.post("/api/trading/preview", json=trade)
        r.raise_for_status()
        return r.json()

    def execute_trade(self, trade: dict) -> dict:
        r = self._client.post("/api/trading/execute", json=trade)
        r.raise_for_status()
        return r.json()

    def get_orders(self) -> list[dict]:
        r = self._client.get("/api/trading/orders")
        r.raise_for_status()
        return r.json()

    def cancel_order(self, order_id: str) -> dict:
        r = self._client.delete(f"/api/trading/orders/{order_id}")
        r.raise_for_status()
        return r.json()

    def get_positions(self) -> list[dict]:
        r = self._client.get("/api/trading/positions")
        r.raise_for_status()
        return r.json()

    def get_account(self) -> dict:
        r = self._client.get("/api/trading/account")
        r.raise_for_status()
        return r.json()

    def get_trade_log(self, limit: int = 50) -> list[dict]:
        r = self._client.get("/api/trading/log", params={"limit": limit})
        r.raise_for_status()
        return r.json()

    # ------------------------------------------------------------------
    # Health
    # ------------------------------------------------------------------

    def health(self) -> dict:
        r = self._client.get("/api/health")
        r.raise_for_status()
        return r.json()

    def close(self) -> None:
        self._client.close()
