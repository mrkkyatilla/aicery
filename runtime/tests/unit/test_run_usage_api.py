import pytest
from fastapi.testclient import TestClient

from core.domain.usage import LlmUsage
from runtime.adapters.db import session as session_mod
from runtime.adapters.db.models import Base
from runtime.adapters.db.trace_repository import TraceRepository
from runtime.adapters.events.emitter import RunEventEmitter
from runtime.adapters.events.factory import reset_event_publisher, set_test_publisher
from runtime.adapters.events.memory_publisher import InMemoryEventPublisher
from runtime.adapters.langgraph_orchestrator import LangGraphOrchestrator
from runtime.adapters.providers.mock import MockProvider
from runtime.api import deps as deps_mod
from runtime.api.app import create_app
from runtime.api.deps import _get_emitter
from runtime.api.rate_limit import reset_rate_limiter
from runtime.services.trace_recorder import TraceRecorder


@pytest.fixture
def usage_client(monkeypatch):
    monkeypatch.setenv("API_KEY", "dev")
    monkeypatch.setenv("USE_MOCK_PROVIDER", "true")
    monkeypatch.setenv("DATABASE_URL", "sqlite://")
    monkeypatch.setenv("NATS_ENABLED", "false")
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
        yield client, engine
    set_test_publisher(None)
    reset_event_publisher()
    reset_rate_limiter()


def test_get_run_usage_aggregates_llm_steps(usage_client):
    client, engine = usage_client
    created = client.post(
        "/v1/runs",
        json={"agent_id": "echo", "input": "hello", "execute": False},
        headers={"X-API-Key": "dev"},
    )
    assert created.status_code == 201
    run_id = created.json()["id"]

    factory = session_mod.get_session_factory()
    session = factory()
    try:
        recorder = TraceRecorder(TraceRepository(session))
        recorder.record_llm(
            run_id=run_id,
            name="provider.stream",
            messages=[{"role": "user", "content": "hello"}],
            output="echo:hello",
            model="mock",
            usage=LlmUsage(provider="mock", model="mock", tokens_in=12, tokens_out=8),
        )
    finally:
        session.close()

    response = client.get(f"/v1/runs/{run_id}/usage", headers={"X-API-Key": "dev"})
    assert response.status_code == 200
    body = response.json()
    assert body["tokens_in"] == 12
    assert body["tokens_out"] == 8
    assert body["llm_calls"] == 1
    assert body["lines"][0]["provider"] == "mock"


def test_echo_run_trace_includes_usage(usage_client):
    client, _engine = usage_client
    created = client.post(
        "/v1/runs",
        json={"agent_id": "echo", "input": "hello", "execute": True},
        headers={"X-API-Key": "dev"},
    )
    run_id = created.json()["id"]
    for _ in range(60):
        body = client.get(f"/v1/runs/{run_id}", headers={"X-API-Key": "dev"}).json()
        if body["status"] in ("completed", "failed", "cancelled"):
            break
    trace = client.get(f"/v1/runs/{run_id}/trace", headers={"X-API-Key": "dev"}).json()
    llm_steps = [s for s in trace["steps"] if s["type"] == "llm"]
    assert llm_steps
    assert llm_steps[0]["usage"] is not None
    assert llm_steps[0]["usage"]["tokens_out"] >= 1
