from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from backend.config import settings
from backend.routers import chat, market, portfolio, trading
from backend.services import ServiceContainer
from backend.services.cache_service import CacheService
from backend.services.market_data_service import MarketDataService
from backend.services.portfolio_service import PortfolioService


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting InvestDash API")
    cache = CacheService(settings.cache_db_path)
    market_data = MarketDataService(cache)
    portfolio_svc = PortfolioService(market_data)

    container = ServiceContainer(
        cache=cache,
        market_data=market_data,
        portfolio=portfolio_svc,
    )

    # AI engine (optional)
    if settings.anthropic_api_key:
        try:
            from backend.services.ai_engine import AIEngine

            container.ai_engine = AIEngine(portfolio_svc, market_data)  # type: ignore[attr-defined]
            logger.info("AI engine initialized")
        except Exception as e:
            logger.warning("AI engine failed to initialize: {}", e)
    else:
        logger.info("No ANTHROPIC_API_KEY — AI chat disabled")

    # Trading (optional)
    if settings.alpaca_api_key and settings.alpaca_secret_key:
        try:
            from backend.services.trading_service import TradingService

            container.trading = TradingService(market_data, portfolio_svc)
            logger.info("Trading service initialized (paper={})", settings.alpaca_paper)
        except Exception as e:
            logger.warning("Trading service failed to initialize: {}", e)
    else:
        logger.info("No Alpaca keys — trading disabled")

    app.state.services = container
    yield
    cache.close()
    logger.info("InvestDash API stopped")


app = FastAPI(
    title="InvestDash API",
    version="5.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(portfolio.router)
app.include_router(market.router)
app.include_router(chat.router)
app.include_router(trading.router)


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "version": "5.0.0",
        "ai_available": settings.anthropic_api_key is not None,
        "trading_available": settings.alpaca_api_key is not None,
    }


def main():
    import uvicorn

    uvicorn.run(
        "backend.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
    )


if __name__ == "__main__":
    main()
