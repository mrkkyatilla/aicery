from fastapi.testclient import TestClient

from gateway.adapters.db.repositories import OrgRepository, RunLinkRepository, WorkspaceRepository
from gateway.adapters.db.session import get_session_factory
from gateway.api.app import create_app


def test_proxy_create_run(monkeypatch, tenant_headers):
    headers, _org_id = tenant_headers

    class FakeResponse:
        status_code = 201

        def json(self):
            return {"id": "run-proxy-1", "status": "pending"}

    async def fake_request(self, method, path, **kwargs):
        assert method == "POST"
        assert path == "/v1/runs"
        assert kwargs["json"]["workspace_id"] == "tenant-ws"
        return FakeResponse()

    monkeypatch.setattr(
        "gateway.adapters.aicery.client.AiceryRuntimeClient.request",
        fake_request,
    )

    client = TestClient(create_app())
    response = client.post(
        "/v1/runs",
        json={"agent_id": "echo", "input": "hello", "execute": False},
        headers=headers,
    )
    assert response.status_code == 201

    factory = get_session_factory()
    session = factory()
    link = RunLinkRepository(session).get("run-proxy-1")
    assert link is not None
    session.close()


def test_cross_tenant_run_forbidden(tenant_headers):
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
    response = client.get("/v1/runs/secret-run", headers=headers)
    assert response.status_code == 404
