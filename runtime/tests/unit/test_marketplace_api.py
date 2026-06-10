from fastapi.testclient import TestClient

from runtime.api.app import create_app

REQUIRED_FIELDS = ("id", "slug", "name", "type", "version", "trust_level")


def test_list_plugins_200() -> None:
    with TestClient(create_app()) as client:
        response = client.get("/v1/marketplace/plugins", headers={"X-API-Key": "dev"})
    assert response.status_code == 200
    body = response.json()
    assert len(body["plugins"]) >= 3


def test_plugin_schema_fields() -> None:
    with TestClient(create_app()) as client:
        response = client.get("/v1/marketplace/plugins", headers={"X-API-Key": "dev"})
    assert response.status_code == 200
    for plugin in response.json()["plugins"]:
        for field in REQUIRED_FIELDS:
            assert field in plugin, f"missing {field} on {plugin.get('slug')}"
        assert plugin["trust_level"] in ("verified", "community")


def test_list_plugins_401_without_auth() -> None:
    with TestClient(create_app()) as client:
        response = client.get("/v1/marketplace/plugins")
    assert response.status_code == 401


def test_list_plugins_includes_showcase_slugs() -> None:
    with TestClient(create_app()) as client:
        response = client.get("/v1/marketplace/plugins", headers={"X-API-Key": "dev"})
    slugs = {p["slug"] for p in response.json()["plugins"]}
    assert "workspace-analyst" in slugs
    assert "stock-advisor" in slugs
