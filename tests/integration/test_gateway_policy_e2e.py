"""Gateway JWT, rate-limit, and max_graph_steps via compose stack."""

from __future__ import annotations

import os
import time
import uuid

import httpx
import pytest

pytestmark = [pytest.mark.integration, pytest.mark.gateway_policy_e2e]

GATEWAY_BASE = os.environ.get("AICERY_GATEWAY_URL", "http://localhost:8081")
RUNTIME_BASE = os.environ.get("AICERY_API_URL", "http://localhost:8000")
RUNTIME_API_KEY = os.environ.get("AICERY_API_KEY", "dev")
ADMIN_TOKEN = os.environ.get("GATEWAY_ADMIN_TOKEN", "admin-dev")
ADMIN_HEADERS = {"X-Admin-Token": ADMIN_TOKEN}


def _gateway_reachable() -> bool:
    try:
        with httpx.Client(timeout=2.0) as client:
            return client.get(f"{GATEWAY_BASE}/health").is_success
    except httpx.HTTPError:
        return False


@pytest.fixture
def gw_client() -> httpx.Client:
    if not _gateway_reachable():
        pytest.skip("Gateway not reachable — run gate-gateway-policy-e2e")
    with httpx.Client(base_url=GATEWAY_BASE, timeout=60.0) as client:
        yield client


def _provision_org(client: httpx.Client) -> tuple[str, str]:
    org = client.post("/admin/orgs", json={"name": f"e2e-{uuid.uuid4().hex[:8]}"}, headers=ADMIN_HEADERS)
    org.raise_for_status()
    org_id = org.json()["id"]
    ws = client.post(
        f"/admin/orgs/{org_id}/workspaces",
        json={"name": "default", "runtime_workspace_id": "local"},
        headers=ADMIN_HEADERS,
    )
    ws.raise_for_status()
    key_resp = client.post(
        f"/admin/orgs/{org_id}/api-keys",
        headers=ADMIN_HEADERS,
    )
    key_resp.raise_for_status()
    return org_id, key_resp.json()["key"]


def test_gateway_jwt_create_run(gw_client: httpx.Client) -> None:
    from gateway.config import Settings
    from gateway.services.jwt_auth import issue_tenant_token

    settings = Settings()
    if not settings.jwt_enabled:
        pytest.skip("Gateway JWT_ENABLED=false — run gate-gateway-policy-e2e")
    org_id, _api_key = _provision_org(gw_client)
    token = issue_tenant_token(uuid.UUID(org_id), settings=settings)
    response = gw_client.post(
        "/v1/runs",
        json={"agent_id": "echo", "input": "jwt e2e", "execute": False},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    assert response.json()["agent_id"] == "echo"


def test_gateway_rate_limit_429(gw_client: httpx.Client) -> None:
    _, api_key = _provision_org(gw_client)
    headers = {"X-Api-Key": api_key}
    responses = [gw_client.get("/v1/agents", headers=headers) for _ in range(8)]
    assert any(r.status_code == 429 for r in responses)
    limited = next(r for r in responses if r.status_code == 429)
    detail = limited.json().get("detail", {})
    if isinstance(detail, dict):
        assert detail.get("error_code") == "RATE_LIMITED"


def test_gateway_max_graph_steps_proxy(gw_client: httpx.Client) -> None:
    org_id, api_key = _provision_org(gw_client)
    patch = gw_client.patch(
        f"/admin/orgs/{org_id}",
        json={"max_graph_steps": 2},
        headers=ADMIN_HEADERS,
    )
    patch.raise_for_status()
    headers = {"X-Api-Key": api_key}
    created = gw_client.post(
        "/v1/runs",
        json={
            "agent_id": "research",
            "pipeline": "research-chain",
            "input": "step limit e2e",
            "execute": True,
        },
        headers=headers,
    )
    created.raise_for_status()
    run_id = created.json()["id"]

    deadline = time.monotonic() + 90.0
    last: dict | None = None
    runtime_headers = {"X-API-Key": RUNTIME_API_KEY}
    with httpx.Client(base_url=RUNTIME_BASE, timeout=60.0) as runtime_client:
        while time.monotonic() < deadline:
            response = runtime_client.get(f"/v1/runs/{run_id}", headers=runtime_headers)
            response.raise_for_status()
            last = response.json()
            if last.get("status") in ("failed", "completed"):
                break
            time.sleep(0.3)

    assert last is not None
    assert last.get("status") == "failed"
    assert last.get("error_code") == "GRAPH_STEP_LIMIT"
