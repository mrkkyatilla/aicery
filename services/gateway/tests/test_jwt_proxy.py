import uuid

import pytest
from fastapi.testclient import TestClient

from gateway.adapters.db import session as session_mod
from gateway.adapters.db.models import Base
from gateway.adapters.db.repositories import OrgRepository, WorkspaceRepository
from gateway.api.app import create_app
from gateway.services.jwt_auth import issue_tenant_token
from gateway.services.rate_limit import reset_rate_limiter


@pytest.fixture
def jwt_client(monkeypatch):
    monkeypatch.setenv("GATEWAY_DATABASE_URL", "sqlite://")
    monkeypatch.setenv("JWT_ENABLED", "true")
    monkeypatch.setenv("JWT_SECRET", "gateway-test-secret-32bytes-long!!")
    monkeypatch.setenv("RATE_LIMIT_ENABLED", "false")

    reset_rate_limiter()
    session_mod._engine = None
    session_mod._SessionLocal = None
    engine = session_mod.get_engine("sqlite://")
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

    session = session_mod.get_session_factory()()
    org = OrgRepository(session).create("jwt-org")
    WorkspaceRepository(session).create(
        org_id=org.id, name="default", runtime_workspace_id="jwt-ws"
    )
    org_id = org.id
    session.close()

    app = create_app()
    with TestClient(app) as client:
        token = issue_tenant_token(org_id)
        yield client, token
    reset_rate_limiter()


def test_proxy_route_with_bearer_jwt(jwt_client, monkeypatch):
    client, token = jwt_client

    async def fake_request(self, method, path, **kwargs):
        class Resp:
            status_code = 200

            def json(self):
                return {"agent_id": "echo", "confidence": 1.0, "reason": "jwt"}

        return Resp()

    monkeypatch.setattr(
        "gateway.adapters.aicery.client.AiceryRuntimeClient.request",
        fake_request,
    )

    response = client.post(
        "/v1/route",
        headers={"Authorization": f"Bearer {token}"},
        json={"input": "hello"},
    )
    assert response.status_code == 200
    assert response.json()["agent_id"] == "echo"
