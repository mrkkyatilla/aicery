import pytest
from fastapi.testclient import TestClient

from runtime.adapters.db import session as session_mod
from runtime.adapters.db.models import Base
from runtime.api.app import create_app
from runtime.api.rate_limit import reset_rate_limiter


@pytest.fixture
def route_llm_client(monkeypatch):
    monkeypatch.setenv("API_KEY", "dev")
    monkeypatch.setenv("USE_MOCK_PROVIDER", "true")
    monkeypatch.setenv("ROUTER_LLM_ENABLED", "true")
    monkeypatch.setenv("DATABASE_URL", "sqlite://")
    monkeypatch.setenv("NATS_ENABLED", "false")
    monkeypatch.setenv("RATE_LIMIT_BACKEND", "memory")

    reset_rate_limiter()
    session_mod._engine = None
    session_mod._SessionLocal = None
    engine = session_mod.get_engine("sqlite://")
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

    with TestClient(create_app()) as client:
        yield client


def test_route_endpoint_llm_enabled(route_llm_client):
    response = route_llm_client.post(
        "/v1/route",
        json={"input": "What does our refund policy say?"},
        headers={"X-API-Key": "dev"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["agent_id"] == "research"
    assert 0.0 <= body["confidence"] <= 1.0
    assert body["reason"]
    assert body["reason"].startswith("llm:") or body["reason"].startswith("rule:")


def test_route_endpoint_rule_short_circuit(route_llm_client):
    response = route_llm_client.post(
        "/v1/route",
        json={"input": "hello"},
        headers={"X-API-Key": "dev"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["agent_id"] == "echo"
    assert body["reason"].startswith("rule:")
