import json
import sqlite3
from pathlib import Path

from loguru import logger


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def get_cache_connection(db_path: Path) -> sqlite3.Connection:
    _ensure_parent(db_path)
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS cache (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            expires_at REAL NOT NULL,
            created_at REAL NOT NULL DEFAULT (strftime('%s', 'now'))
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_cache_expires ON cache(expires_at)")
    conn.commit()
    logger.debug("Cache DB ready at {}", db_path)
    return conn


def get_trade_connection(db_path: Path) -> sqlite3.Connection:
    _ensure_parent(db_path)
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS trade_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL DEFAULT (datetime('now')),
            broker TEXT NOT NULL,
            account_mode TEXT NOT NULL,
            symbol TEXT NOT NULL,
            side TEXT NOT NULL,
            quantity REAL NOT NULL,
            order_type TEXT NOT NULL,
            limit_price REAL,
            stop_price REAL,
            status TEXT NOT NULL,
            order_id TEXT,
            filled_price REAL,
            filled_quantity REAL,
            portfolio_value_at_trade REAL,
            order_pct_of_portfolio REAL,
            ai_suggested INTEGER DEFAULT 0,
            notes TEXT
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_trade_timestamp ON trade_log(timestamp)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_trade_symbol ON trade_log(symbol)")
    conn.commit()
    logger.debug("Trade DB ready at {}", db_path)
    return conn
