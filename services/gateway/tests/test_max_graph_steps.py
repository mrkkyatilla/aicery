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
def steps_client(monkeypatch):
    monkeypatch.setenv("GATEWAY_DATABASE_URL", "sqlite://")
    monkeypatch.setenv("RATE_LIMIT_ENABLED", "false")

    reset_rate_limiter()
    session_mod._engine = None
    session_mod._SessionLocal = None
    engine = session_mod.get_engine("sqlite://")
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

    session = session_mod.get_session_factory()()
    org = OrgRepository(session).create("steps-org")
    OrgRepository(session).update_max_graph_steps(org.id, 5)
    key = "aic_test_steps_key_12345678901234567890123"
    ApiKeyRepository(session).create(
        org_id=org.id,
        key_hash=hash_api_key(key),
        key_prefix=key[:12],
        name="default",
    )
    WorkspaceRepository(session).create(
        org_id=org.id, name="default", runtime_workspace_id="steps-ws"
    )
    session.close()

    app = create_app()
    with TestClient(app) as client:
        yield client, key
    reset_rate_limiter()


def test_proxy_create_run_sends_max_steps_header(steps_client, monkeypatch):
    client, key = steps_client
    captured: dict = {}

    async def fake_request(self, method, path, **kwargs):
        captured["headers"] = kwargs.get("extra_headers") or {}

        class Resp:
            status_code = 201

            def json(self):
                return {"id": str(uuid.uuid4()), "status": "pending"}

        return Resp()

    monkeypatch.setattr(
        "gateway.adapters.aicery.client.AiceryRuntimeClient.request",
        fake_request,
    )

    response = client.post(
        "/v1/runs",
        headers={"X-Api-Key": key},
        json={"agent_id": "echo", "input": "hi", "execute": False},
    )
    assert response.status_code == 201
    assert captured["headers"].get("X-Aicery-Max-Steps") == "5"
