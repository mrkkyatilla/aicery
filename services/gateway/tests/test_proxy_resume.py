import pytest
from fastapi.testclient import TestClient

from gateway.adapters.db.repositories import OrgRepository, RunLinkRepository, WorkspaceRepository
from gateway.adapters.db.session import get_session_factory
from gateway.api.app import create_app


def test_proxy_resume_run(monkeypatch, tenant_headers):
    headers, org_id = tenant_headers
    captured: dict = {}

    class FakeResponse:
        status_code = 200

        def json(self):
            return {"id": "run-proxy-1", "status": "running"}

    async def fake_request(self, method, path, **kwargs):
        captured["method"] = method
        captured["path"] = path
        captured["json"] = kwargs.get("json")
        captured["headers"] = kwargs.get("extra_headers")
        return FakeResponse()

    monkeypatch.setattr(
        "gateway.adapters.aicery.client.AiceryRuntimeClient.request",
        fake_request,
    )

    factory = get_session_factory()
    session = factory()
    RunLinkRepository(session).create(
        run_id="run-proxy-1",
        org_id=org_id,
        workspace_id=WorkspaceRepository(session).get_default(org_id).id,
    )
    session.close()

    client = TestClient(create_app())
    response = client.post(
        "/v1/runs/run-proxy-1/resume",
        json={"decision": "approve", "approval_id": "ap-1"},
        headers=headers,
    )
    assert response.status_code == 200
    assert captured["method"] == "POST"
    assert captured["path"] == "/v1/runs/run-proxy-1/resume"
    assert captured["json"]["decision"] == "approve"
    assert captured["headers"]["X-Aicery-Org-Id"] == str(org_id)


def test_proxy_resume_cross_tenant_forbidden(tenant_headers):
    headers, _ = tenant_headers
    factory = get_session_factory()
    session = factory()
    other = OrgRepository(session).create("other")
    ws = WorkspaceRepository(session).create(
        org_id=other.id, name="w", runtime_workspace_id="other-ws"
    )
    RunLinkRepository(session).create(
        run_id="secret-run", org_id=other.id, workspace_id=ws.id
    )
    session.close()

    client = TestClient(create_app())
    response = client.post(
        "/v1/runs/secret-run/resume",
        json={"decision": "approve"},
        headers=headers,
    )
    assert response.status_code == 404
