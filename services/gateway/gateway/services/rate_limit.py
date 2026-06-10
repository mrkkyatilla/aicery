from __future__ import annotations

import logging
import time
from typing import Protocol

from core.domain.error_codes import ErrorCode

from gateway.config import Settings

logger = logging.getLogger(__name__)


class GatewayRateLimitedError(Exception):
    error_code = ErrorCode.RATE_LIMITED

    def __init__(self, *, limit: int, window_seconds: int = 60) -> None:
        super().__init__(f"Rate limit exceeded: {limit} requests per {window_seconds}s")
        self.limit = limit


class RateLimiterPort(Protocol):
    async def allow(self, key: str) -> bool: ...


class MemoryRateLimiter:
    def __init__(self, *, limit: int) -> None:
        self._limit = limit
        self._counts: dict[str, tuple[int, int]] = {}

    async def allow(self, key: str) -> bool:
        window = int(time.time()) // 60
        bucket_key = f"{key}:{window}"
        current_window, count = self._counts.get(bucket_key, (window, 0))
        if current_window != window:
            count = 0
        count += 1
        self._counts[bucket_key] = (window, count)
        return count <= self._limit


class RedisRateLimiter:
    def __init__(self, *, redis_url: str, limit: int) -> None:
        self._limit = limit
        self._redis_url = redis_url
        self._client = None

    def _get_client(self):
        if self._client is None:
            import redis

            self._client = redis.from_url(self._redis_url, decode_responses=True)
        return self._client

    async def allow(self, key: str) -> bool:
        import asyncio

        window = int(time.time()) // 60
        redis_key = f"gw:rl:{key}:{window}"

        def _incr() -> int:
            client = self._get_client()
            pipe = client.pipeline()
            pipe.incr(redis_key)
            pipe.expire(redis_key, 120)
            results = pipe.execute()
            return int(results[0])

        count = await asyncio.to_thread(_incr)
        return count <= self._limit


_limiter: RateLimiterPort | None = None


def reset_rate_limiter() -> None:
    global _limiter
    _limiter = None


def get_rate_limiter() -> RateLimiterPort:
    global _limiter
    if _limiter is not None:
        return _limiter
    settings = Settings()
    if settings.rate_limit_backend == "memory":
        _limiter = MemoryRateLimiter(limit=settings.rate_limit_per_minute)
    else:
        try:
            _limiter = RedisRateLimiter(
                redis_url=settings.redis_url,
                limit=settings.rate_limit_per_minute,
            )
        except Exception:
            logger.warning("Gateway Redis rate limiter unavailable; using memory")
            _limiter = MemoryRateLimiter(limit=settings.rate_limit_per_minute)
    return _limiter


async def check_rate_limit(org_id: str) -> None:
    settings = Settings()
    if not settings.rate_limit_enabled:
        return
    allowed = await get_rate_limiter().allow(org_id)
    if not allowed:
        raise GatewayRateLimitedError(limit=settings.rate_limit_per_minute)
