import pytest
from fastapi.testclient import TestClient

from runtime.adapters.db import session as session_mod
from runtime.adapters.db.models import Base
from runtime.adapters.events.emitter import RunEventEmitter
from runtime.adapters.events.factory import reset_event_publisher, set_test_publisher
from runtime.adapters.events.memory_publisher import InMemoryEventPublisher
from runtime.adapters.langgraph_orchestrator import LangGraphOrchestrator
from runtime.adapters.providers.mock import MockProvider
from runtime.api import deps as deps_mod
from runtime.api.app import create_app
from runtime.api.deps import _get_emitter
from runtime.api.rate_limit import MemoryRateLimiter, reset_rate_limiter


@pytest.fixture
def rate_client(monkeypatch):
    monkeypatch.setenv("API_KEY", "dev")
    monkeypatch.setenv("USE_MOCK_PROVIDER", "true")
    monkeypatch.setenv("DATABASE_URL", "sqlite://")
    monkeypatch.setenv("NATS_ENABLED", "false")
    monkeypatch.setenv("RATE_LIMIT_ENABLED", "true")
    monkeypatch.setenv("RATE_LIMIT_PER_MINUTE", "3")
    monkeypatch.setenv("RATE_LIMIT_BACKEND", "memory")

    reset_rate_limiter()
    session_mod._engine = None
    session_mod._SessionLocal = None
    engine = session_mod.get_engine("sqlite://")
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

    publisher = InMemoryEventPublisher()
    set_test_publisher(publisher)
    app = create_app()

    async def override_emitter():
        return RunEventEmitter(publisher)

    app.dependency_overrides[_get_emitter] = override_emitter
    deps_mod._orchestrator = LangGraphOrchestrator(provider=MockProvider())

    with TestClient(app) as client:
        yield client
    set_test_publisher(None)
    reset_event_publisher()
    reset_rate_limiter()


def test_memory_rate_limiter_blocks_after_limit() -> None:
    import asyncio

    limiter = MemoryRateLimiter(limit=3)

    async def _run() -> None:
        assert await limiter.allow("k")
        assert await limiter.allow("k")
        assert await limiter.allow("k")
        assert not await limiter.allow("k")

    asyncio.run(_run())


def test_api_returns_429_when_rate_limited(rate_client) -> None:
    headers = {"X-API-Key": "dev"}
    for _ in range(3):
        assert rate_client.get("/v1/agents", headers=headers).status_code == 200
    blocked = rate_client.get("/v1/agents", headers=headers)
    assert blocked.status_code == 429
    body = blocked.json()
    assert body.get("error_code") == "RATE_LIMITED"
