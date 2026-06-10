import uuid

import pytest
from fastapi.testclient import TestClient

from gateway.adapters.db import session as session_mod
from gateway.adapters.db.models import Base
from gateway.adapters.db.repositories import ApiKeyRepository, OrgRepository, WorkspaceRepository
from gateway.api.app import create_app
from gateway.services.auth import hash_api_key
from gateway.services.rate_limit import reset_rate_limiter


@pytest.fixture
def rl_client(monkeypatch):
    monkeypatch.setenv("GATEWAY_DATABASE_URL", "sqlite://")
    monkeypatch.setenv("RATE_LIMIT_ENABLED", "true")
    monkeypatch.setenv("RATE_LIMIT_PER_MINUTE", "2")
    monkeypatch.setenv("RATE_LIMIT_BACKEND", "memory")

    reset_rate_limiter()
    session_mod._engine = None
    session_mod._SessionLocal = None
    engine = session_mod.get_engine("sqlite://")
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

    session = session_mod.get_session_factory()()
    org = OrgRepository(session).create("rl-org")
    key = "aic_test_rl_key_123456789012345678901234"
    ApiKeyRepository(session).create(
        org_id=org.id,
        key_hash=hash_api_key(key),
        key_prefix=key[:12],
        name="default",
    )
    WorkspaceRepository(session).create(
        org_id=org.id, name="default", runtime_workspace_id="rl-ws"
    )
    session.close()

    app = create_app()
    with TestClient(app) as client:
        yield client, key
    reset_rate_limiter()


def test_gateway_rate_limit_returns_429(rl_client, monkeypatch):
    client, key = rl_client
    headers = {"X-Api-Key": key}

    async def fake_request(self, method, path, **kwargs):
        class Resp:
            status_code = 200

            def json(self):
                return {"agent_id": "echo", "confidence": 1.0, "reason": "test"}

        return Resp()

    monkeypatch.setattr(
        "gateway.adapters.aicery.client.AiceryRuntimeClient.request",
        fake_request,
    )

    for _ in range(2):
        response = client.post("/v1/route", headers=headers, json={"input": "hi"})
        assert response.status_code == 200

    response = client.post("/v1/route", headers=headers, json={"input": "hi"})
    assert response.status_code == 429
    body = response.json()
    assert body["detail"]["error_code"] == "RATE_LIMITED"
