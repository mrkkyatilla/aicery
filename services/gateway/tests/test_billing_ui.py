"""E8 — Billing dashboard static UI + API wiring."""

from fastapi.testclient import TestClient

from gateway.adapters.db.repositories import ApiKeyRepository, OrgRepository, UsageRepository
from gateway.adapters.db.session import get_session_factory
from gateway.api.app import create_app
from gateway.services.auth import generate_api_key, hash_api_key


def _tenant_headers() -> tuple[dict[str, str], str]:
    factory = get_session_factory()
    session = factory()
    org = OrgRepository(session).create("ui-test-org")
    key = generate_api_key()
    ApiKeyRepository(session).create(
        org_id=org.id,
        key_hash=hash_api_key(key),
        key_prefix=key[:12],
        name="ui",
    )
    UsageRepository(session).record(
        org_id=org.id,
        workspace_id="local",
        run_id="run-ui-1",
        metric="agent_run",
        quantity=10,
    )
    UsageRepository(session).record(
        org_id=org.id,
        workspace_id="local",
        run_id="run-ui-1",
        metric="llm_tokens_out",
        quantity=1200,
        unit="token",
    )
    org_id = str(org.id)
    session.close()
    return {"X-Api-Key": key}, org_id


def test_billing_dashboard_html():
    client = TestClient(create_app())
    response = client.get("/ui/billing")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
    assert "Billing &amp; usage" in response.text or "Billing & usage" in response.text
    assert "/ui/billing/app.js" in response.text


def test_billing_static_assets():
    client = TestClient(create_app())
    css = client.get("/ui/billing/styles.css")
    js = client.get("/ui/billing/app.js")
    assert css.status_code == 200
    assert js.status_code == 200
    assert ".bar-fill" in css.text
    assert "startCheckout" in js.text


def test_billing_success_and_cancel_pages():
    client = TestClient(create_app())
    assert client.get("/ui/billing/success").status_code == 200
    assert client.get("/ui/billing/cancel").status_code == 200


def test_billing_me_api_matches_ui_contract():
    client = TestClient(create_app())
    headers, org_id = _tenant_headers()
    response = client.get("/billing/me", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["org_id"] == org_id
    assert body["tier"] == "free"
    assert body["usage"]["agent_run"] == 10
    assert body["limits"]["agent_run"] == 100


def test_billing_checkout_without_stripe_returns_400():
    client = TestClient(create_app())
    headers, _ = _tenant_headers()
    response = client.post(
        "/billing/checkout",
        headers=headers,
        json={"tier": "pro"},
    )
    assert response.status_code == 400
