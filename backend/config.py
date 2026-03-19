from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Paths
    portfolio_path: Path = Path("data/portfolio_manual.json")
    cache_db_path: Path = Path("data/cache.db")
    trade_db_path: Path = Path("data/trades.db")

    # API Keys (all optional)
    anthropic_api_key: Optional[str] = None
    alpha_vantage_key: Optional[str] = None
    fmp_api_key: Optional[str] = None
    fred_api_key: Optional[str] = None

    # Trading
    alpaca_api_key: Optional[str] = None
    alpaca_secret_key: Optional[str] = None
    alpaca_paper: bool = True
    alpaca_base_url: str = "https://paper-api.alpaca.markets"

    # Optional integrations
    plaid_client_id: Optional[str] = None
    plaid_secret: Optional[str] = None
    plaid_env: str = "sandbox"
    public_access_token: Optional[str] = None
    uw_api_key: Optional[str] = None

    # Server
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    debug: bool = False
    dashboard_api_key: Optional[str] = None

    # CORS
    cors_origins: list[str] = ["http://localhost:8501", "http://localhost:3000"]
    cors_allow_methods: list[str] = ["GET", "POST", "DELETE"]
    cors_allow_headers: list[str] = ["Content-Type", "X-API-Key"]

    # Cache TTLs (seconds)
    cache_ttl_quote: int = 60
    cache_ttl_historical: int = 86400
    cache_ttl_fundamentals: int = 86400
    cache_ttl_sector_info: int = 604800
    cache_ttl_macro: int = 3600
    cache_ttl_crypto: int = 30
    cache_ttl_defi_yields: int = 300
    cache_ttl_gold_spot: int = 60

    # Trading Safety
    max_single_order_pct: float = 0.10
    max_single_order_usd: float = 10_000
    require_trade_confirmation: bool = True
    paper_mode_default: bool = True
    daily_trade_limit: int = 20
    log_all_trades: bool = True


settings = Settings()
