import json
import time
from pathlib import Path
from typing import Any, Optional

from loguru import logger

from backend.database import get_cache_connection
from backend.exceptions import CacheError


class CacheService:
    def __init__(self, db_path: Path) -> None:
        try:
            self._conn = get_cache_connection(db_path)
        except Exception as e:
            raise CacheError(f"Failed to initialize cache: {e}") from e

    def get(self, key: str) -> Optional[Any]:
        """Return cached value if it exists and hasn't expired."""
        try:
            row = self._conn.execute(
                "SELECT value FROM cache WHERE key = ? AND expires_at > ?",
                (key, time.time()),
            ).fetchone()
            if row is None:
                return None
            return json.loads(row[0])
        except Exception as e:
            logger.warning("Cache get error for key={}: {}", key, e)
            return None

    def get_stale(self, key: str) -> Optional[Any]:
        """Return cached value even if expired (fallback for API failures)."""
        try:
            row = self._conn.execute(
                "SELECT value FROM cache WHERE key = ?",
                (key,),
            ).fetchone()
            if row is None:
                return None
            return json.loads(row[0])
        except Exception as e:
            logger.warning("Cache get_stale error for key={}: {}", key, e)
            return None

    def set(self, key: str, value: Any, ttl_seconds: int) -> None:
        """Store a value with a TTL."""
        try:
            serialized = json.dumps(value, default=str)
            expires_at = time.time() + ttl_seconds
            self._conn.execute(
                """INSERT INTO cache (key, value, expires_at, created_at)
                   VALUES (?, ?, ?, ?)
                   ON CONFLICT(key) DO UPDATE SET
                       value = excluded.value,
                       expires_at = excluded.expires_at,
                       created_at = excluded.created_at""",
                (key, serialized, expires_at, time.time()),
            )
            self._conn.commit()
        except Exception as e:
            logger.warning("Cache set error for key={}: {}", key, e)

    def invalidate(self, key: str) -> None:
        """Remove a specific key from cache."""
        try:
            self._conn.execute("DELETE FROM cache WHERE key = ?", (key,))
            self._conn.commit()
        except Exception as e:
            logger.warning("Cache invalidate error for key={}: {}", key, e)

    def cleanup(self) -> int:
        """Remove all expired entries. Returns count of removed rows."""
        try:
            cursor = self._conn.execute(
                "DELETE FROM cache WHERE expires_at <= ?",
                (time.time(),),
            )
            self._conn.commit()
            removed = cursor.rowcount
            if removed:
                logger.info("Cache cleanup: removed {} expired entries", removed)
            return removed
        except Exception as e:
            logger.warning("Cache cleanup error: {}", e)
            return 0

    def clear_all(self) -> None:
        """Wipe the entire cache."""
        try:
            self._conn.execute("DELETE FROM cache")
            self._conn.commit()
            logger.info("Cache cleared")
        except Exception as e:
            logger.warning("Cache clear_all error: {}", e)

    def close(self) -> None:
        """Close the database connection."""
        try:
            self._conn.close()
        except Exception:
            pass
