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
from runtime.api.rate_limit import reset_rate_limiter


@pytest.fixture
def policy_client(monkeypatch):
    monkeypatch.setenv("API_KEY", "dev")
    monkeypatch.setenv("USE_MOCK_PROVIDER", "true")
    monkeypatch.setenv("DATABASE_URL", "sqlite://")
    monkeypatch.setenv("NATS_ENABLED", "false")
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


def test_create_run_with_provider_policy(policy_client):
    response = policy_client.post(
        "/v1/runs",
        json={
            "agent_id": "echo",
            "input": "hello",
            "execute": False,
            "provider_policy": {"llm": {"provider": "mock"}},
        },
        headers={"X-API-Key": "dev"},
    )
    assert response.status_code == 201, response.text


def test_create_run_anthropic_without_key_returns_422(policy_client, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    response = policy_client.post(
        "/v1/runs",
        json={
            "agent_id": "echo",
            "input": "hello",
            "execute": False,
            "provider_policy": {"llm": {"provider": "anthropic"}},
        },
        headers={"X-API-Key": "dev"},
    )
    assert response.status_code == 422


def test_create_run_groq_without_key_returns_422(policy_client, monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    response = policy_client.post(
        "/v1/runs",
        json={
            "agent_id": "echo",
            "input": "hello",
            "execute": False,
            "provider_policy": {"llm": {"provider": "groq"}},
        },
        headers={"X-API-Key": "dev"},
    )
    assert response.status_code == 422


def test_create_run_openai_without_key_returns_422(policy_client, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    response = policy_client.post(
        "/v1/runs",
        json={
            "agent_id": "echo",
            "input": "hello",
            "execute": False,
            "provider_policy": {"llm": {"provider": "openai"}},
        },
        headers={"X-API-Key": "dev"},
    )
    assert response.status_code == 422


def test_route_endpoint(policy_client):
    response = policy_client.post(
        "/v1/route",
        json={"input": "Summarize README"},
        headers={"X-API-Key": "dev"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["agent_id"] == "research"
    assert "confidence" in body
