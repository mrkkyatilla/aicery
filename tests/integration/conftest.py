import os
import time

import httpx
import pytest


def _qdrant_ready() -> bool:
    try:
        with httpx.Client(timeout=2.0) as client:
            return client.get("http://localhost:6333/readyz").is_success
    except httpx.HTTPError:
        return False


@pytest.fixture(scope="session")
def qdrant_ready() -> bool:
    return _qdrant_ready()


@pytest.fixture
def require_qdrant(qdrant_ready: bool) -> None:
    if not qdrant_ready:
        pytest.skip("Qdrant not on :6333 — run: make integration or make up")


@pytest.fixture(autouse=True)
def reset_redis_rate_limit_state(request) -> None:
    """Avoid cross-test 429 bleed on shared dev API key (skip for rate-limit hammer test)."""
    if "rate_limit_integration" in request.keywords:
        return
    url = os.environ.get("REDIS_URL", "redis://localhost:6380/0")
    try:
        import redis

        redis.from_url(url, socket_connect_timeout=2).flushdb()
    except Exception:
        pass

DEFAULT_BASE = "http://localhost:8000"
DEFAULT_API_KEY = "dev"
TERMINAL_STATUSES = frozenset({"completed", "failed", "cancelled"})
POLL_TIMEOUT_SEC = 120
POLL_INTERVAL_SEC = 0.25


@pytest.fixture(scope="session")
def api_base_url() -> str:
    return os.environ.get("AICERY_API_URL", DEFAULT_BASE)


@pytest.fixture(scope="session")
def api_headers() -> dict[str, str]:
    key = os.environ.get("AICERY_API_KEY", DEFAULT_API_KEY)
    return {"X-API-Key": key}


@pytest.fixture(scope="session")
def api_client(api_base_url: str, api_headers: dict[str, str]) -> httpx.Client:
    with httpx.Client(base_url=api_base_url, headers=api_headers, timeout=30.0) as client:
        yield client


def poll_run_until_terminal(
    client: httpx.Client,
    run_id: str,
    *,
    timeout_sec: float = POLL_TIMEOUT_SEC,
) -> dict:
    deadline = time.monotonic() + timeout_sec
    last: dict | None = None
    while time.monotonic() < deadline:
        response = client.get(f"/v1/runs/{run_id}")
        response.raise_for_status()
        last = response.json()
        if last["status"] in TERMINAL_STATUSES:
            return last
        time.sleep(POLL_INTERVAL_SEC)
    raise AssertionError(f"Run {run_id} did not reach terminal state within {timeout_sec}s: {last}")
