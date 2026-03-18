"""Simple in-memory rate limiting middleware for FastAPI."""

from __future__ import annotations

import time
from collections import defaultdict
from typing import Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

# Rate limit rules: path prefix -> (max_requests, window_seconds)
RATE_LIMIT_RULES: dict[str, tuple[int, int]] = {
    "/api/trading": (10, 60),
    "/api/chat": (30, 60),
}


class _TokenBucket:
    """Per-key sliding window counter."""

    __slots__ = ("_requests",)

    def __init__(self) -> None:
        # key -> list of timestamps
        self._requests: dict[str, list[float]] = defaultdict(list)

    def is_allowed(self, key: str, max_requests: int, window: int) -> bool:
        now = time.monotonic()
        cutoff = now - window
        # Prune expired entries
        timestamps = self._requests[key]
        self._requests[key] = [t for t in timestamps if t > cutoff]
        if len(self._requests[key]) >= max_requests:
            return False
        self._requests[key].append(now)
        return True


_bucket = _TokenBucket()


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _match_rule(path: str) -> tuple[int, int] | None:
    for prefix, limits in RATE_LIMIT_RULES.items():
        if path.startswith(prefix):
            return limits
    return None


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Applies per-IP rate limiting based on path prefix rules."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        rule = _match_rule(request.url.path)
        if rule is None:
            return await call_next(request)

        max_requests, window = rule
        ip = _client_ip(request)
        key = f"{ip}:{request.url.path.split('/')[2]}"  # e.g. "127.0.0.1:trading"

        if not _bucket.is_allowed(key, max_requests, window):
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests. Please try again later."},
            )

        return await call_next(request)
