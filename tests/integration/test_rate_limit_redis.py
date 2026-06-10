"""T3-E2-03: rate limit with Redis (requires make up)."""

import os

import httpx
import pytest

pytestmark = [pytest.mark.integration, pytest.mark.rate_limit_integration]

BASE = "http://localhost:8000"
HEADERS = {"X-API-Key": "dev"}


def test_rate_limit_101st_request_429() -> None:
    url = os.environ.get("REDIS_URL", "redis://localhost:6380/0")
    try:
        import redis

        redis.from_url(url, socket_connect_timeout=2).flushdb()
    except Exception:
        pytest.skip("Redis not available for rate-limit integration")

    with httpx.Client(base_url=BASE, headers=HEADERS, timeout=30.0) as client:
        if client.get("/health").status_code != 200:
            pytest.skip("API not running — run: make integration")

        last_status = 200
        for i in range(105):
            resp = client.get("/v1/agents")
            last_status = resp.status_code
            if resp.status_code == 429:
                body = resp.json()
                assert body.get("error_code") == "RATE_LIMITED"
                assert i >= 99, f"429 too early at request {i}"
                return
        pytest.fail(
            f"Rate limit not reached after 105 GET /v1/agents (last HTTP {last_status}). "
            "Integration must start API with RATE_LIMIT_ENABLED=true, "
            "RATE_LIMIT_BACKEND=redis, RATE_LIMIT_PER_MINUTE=100 (see Makefile integration)."
        )
