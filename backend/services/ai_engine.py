from __future__ import annotations

from collections import defaultdict
from typing import AsyncIterator

import anthropic
from loguru import logger

from backend.config import settings
from backend.exceptions import AIEngineError
from backend.services.market_data_service import MarketDataService
from backend.services.portfolio_service import PortfolioService

SYSTEM_PROMPT = """You are an AI investment analyst assistant for InvestDash, a personal portfolio dashboard.

You have access to the user's portfolio data and real-time market information. Your role is to:
1. Analyze portfolio composition, risk, and performance
2. Provide market insights and stock analysis
3. Explain financial concepts clearly
4. Suggest portfolio improvements (educational, not financial advice)
5. Compare stocks and help with research

Important guidelines:
- Always remind users this is educational/informational, not financial advice
- Be specific with numbers from the portfolio data
- Highlight risks and diversification concerns
- Use clear, concise language
- When discussing trades, emphasize the paper trading safety mechanism

The user's portfolio includes stocks, ETFs, crypto, gold, bonds, and REITs across multiple accounts."""

MAX_HISTORY = 20


class AIEngine:
    def __init__(
        self,
        portfolio: PortfolioService,
        market_data: MarketDataService,
    ) -> None:
        if not settings.anthropic_api_key:
            raise AIEngineError("ANTHROPIC_API_KEY not configured")
        self._client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        self._portfolio = portfolio
        self._market = market_data
        self._conversations: dict[str, list[dict]] = defaultdict(list)

    async def _build_context(self) -> str:
        """Build a context string with current portfolio data."""
        try:
            summary = await self._portfolio.get_summary()
            return (
                f"\n\nCurrent Portfolio Context:\n"
                f"- Total Value: ${summary.total_value:,.2f}\n"
                f"- Gain/Loss: ${summary.total_gain_loss:,.2f} ({summary.total_gain_loss_pct:+.2f}%)\n"
                f"- Cash: ${summary.total_cash:,.2f}\n"
                f"- Holdings: {summary.num_holdings}\n"
                f"- Top: {summary.top_holding_ticker} ({summary.top_holding_weight_pct:.1f}%)\n"
                f"- Equity: {summary.equity_pct:.1f}% | Crypto: {summary.crypto_pct:.1f}% | "
                f"Gold: {summary.gold_pct:.1f}% | Bond: {summary.bond_pct:.1f}% | REIT: {summary.reit_pct:.1f}%"
            )
        except Exception as e:
            logger.warning("Failed to build portfolio context: {}", e)
            return ""

    async def stream_response(
        self, message: str, conversation_id: str
    ) -> AsyncIterator[str]:
        history = self._conversations[conversation_id]

        # Add user message
        history.append({"role": "user", "content": message})

        # Trim history
        if len(history) > MAX_HISTORY:
            history[:] = history[-MAX_HISTORY:]

        # Build system prompt with live context
        context = await self._build_context()
        system = SYSTEM_PROMPT + context

        try:
            async with self._client.messages.stream(
                model="claude-sonnet-4-20250514",
                max_tokens=2048,
                system=system,
                messages=history,
            ) as stream:
                full_response = ""
                async for text in stream.text_stream:
                    full_response += text
                    yield text

            # Add assistant response to history
            history.append({"role": "assistant", "content": full_response})

        except anthropic.APIError as e:
            logger.error("Anthropic API error: {}", e)
            raise AIEngineError(f"AI service error: {e}")
        except Exception as e:
            logger.error("AI engine error: {}", e)
            raise AIEngineError(f"Unexpected AI error: {e}")

    def clear_conversation(self, conversation_id: str) -> None:
        self._conversations.pop(conversation_id, None)
