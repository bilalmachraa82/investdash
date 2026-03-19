"""Rate limiting, API key auth, and security headers middleware."""

from __future__ import annotations

import ipaddress
import secrets
import time
from collections import defaultdict
from typing import Callable

from fastapi import HTTPException, Request, Response, Security
from fastapi.responses import JSONResponse
from fastapi.security import APIKeyHeader
from starlette.middleware.base import BaseHTTPMiddleware

from backend.config import settings

# ── API Key Authentication ──────────────────────────────────────────

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(api_key: str = Security(_api_key_header)) -> None:
    """Dependency that validates the X-API-Key header.

    If DASHBOARD_API_KEY is not set, auth is disabled (dev mode).
    """
    expected = settings.dashboard_api_key
    if not expected:
        return  # auth disabled — dev mode
    if not api_key or not secrets.compare_digest(api_key, expected):
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


# ── Rate Limiting ───────────────────────────────────────────────────

RATE_LIMIT_RULES: dict[str, tuple[int, int]] = {
    "/api/trading": (10, 60),
    "/api/chat": (30, 60),
    "/api/market": (120, 60),
    "/api/portfolio": (60, 60),
}

# Trusted proxy CIDRs (Docker bridge, localhost)
_TRUSTED_PROXIES = {"127.0.0.1", "::1", "172.16.0.0/12", "10.0.0.0/8"}


def _is_trusted_proxy(ip: str) -> bool:
    try:
        addr = ipaddress.ip_address(ip)
        for cidr in _TRUSTED_PROXIES:
            if "/" in cidr:
                if addr in ipaddress.ip_network(cidr, strict=False):
                    return True
            elif ip == cidr:
                return True
    except ValueError:
        pass
    return False


class _TokenBucket:
    """Per-key sliding window counter."""

    __slots__ = ("_requests",)

    def __init__(self) -> None:
        self._requests: dict[str, list[float]] = defaultdict(list)

    def is_allowed(self, key: str, max_requests: int, window: int) -> bool:
        now = time.monotonic()
        cutoff = now - window
        timestamps = self._requests[key]
        self._requests[key] = [t for t in timestamps if t > cutoff]
        if len(self._requests[key]) >= max_requests:
            return False
        self._requests[key].append(now)
        return True


_bucket = _TokenBucket()


def _client_ip(request: Request) -> str:
    """Extract client IP — only trust X-Forwarded-For from known proxies."""
    real_ip = request.client.host if request.client else "unknown"
    if _is_trusted_proxy(real_ip):
        forwarded = request.headers.get("x-forwarded-for", "")
        if forwarded:
            return forwarded.split(",")[0].strip()
    return real_ip


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
        key = f"{ip}:{request.url.path.split('/')[2]}"

        if not _bucket.is_allowed(key, max_requests, window):
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests. Please try again later."},
            )

        return await call_next(request)


# ── Security Headers ────────────────────────────────────────────────

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Adds standard security headers to every response."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), camera=(), microphone=()"
        return response
