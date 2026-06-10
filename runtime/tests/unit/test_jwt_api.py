import pytest
from fastapi.testclient import TestClient

from runtime.adapters.db import session as session_mod
from runtime.adapters.db.models import Base
from runtime.adapters.events.factory import reset_event_publisher, set_test_publisher
from runtime.adapters.events.memory_publisher import InMemoryEventPublisher
from runtime.adapters.langgraph_orchestrator import LangGraphOrchestrator
from runtime.adapters.providers.mock import MockProvider
from runtime.api import deps as deps_mod
from runtime.api.app import create_app
from runtime.api.jwt_auth import issue_token


@pytest.fixture
def jwt_client(monkeypatch):
    monkeypatch.setenv("API_KEY", "dev")
    monkeypatch.setenv("JWT_ENABLED", "true")
    monkeypatch.setenv("JWT_SECRET", "dev-jwt-secret")
    monkeypatch.setenv("USE_MOCK_PROVIDER", "true")
    monkeypatch.setenv("DATABASE_URL", "sqlite://")
    monkeypatch.setenv("NATS_ENABLED", "false")
    monkeypatch.setenv("RATE_LIMIT_BACKEND", "memory")

    session_mod._engine = None
    session_mod._SessionLocal = None
    engine = session_mod.get_engine("sqlite://")
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

    set_test_publisher(InMemoryEventPublisher())
    app = create_app()
    deps_mod._orchestrator = LangGraphOrchestrator(provider=MockProvider())

    with TestClient(app) as client:
        yield client
    set_test_publisher(None)
    reset_event_publisher()


def test_agents_with_bearer_jwt(jwt_client: TestClient) -> None:
    token = issue_token("dev-user")
    response = jwt_client.get(
        "/v1/agents",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200


def test_jwt_disabled_requires_api_key(monkeypatch) -> None:
    monkeypatch.setenv("API_KEY", "dev")
    monkeypatch.setenv("JWT_ENABLED", "false")
    monkeypatch.setenv("USE_MOCK_PROVIDER", "true")
    monkeypatch.setenv("DATABASE_URL", "sqlite://")
    monkeypatch.setenv("NATS_ENABLED", "false")
    monkeypatch.setenv("RATE_LIMIT_BACKEND", "memory")

    session_mod._engine = None
    session_mod._SessionLocal = None
    engine = session_mod.get_engine("sqlite://")
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

    set_test_publisher(InMemoryEventPublisher())
    app = create_app()
    deps_mod._orchestrator = LangGraphOrchestrator(provider=MockProvider())
    with TestClient(app) as client:
        no_key = client.get("/v1/agents")
        assert no_key.status_code == 401
        ok = client.get("/v1/agents", headers={"X-API-Key": "dev"})
        assert ok.status_code == 200
    set_test_publisher(None)
    reset_event_publisher()
