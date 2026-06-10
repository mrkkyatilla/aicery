import pytest
from fastapi.testclient import TestClient
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from gateway.adapters.aicery.client import AiceryRuntimeClient
from gateway.api.app import create_app
from gateway.config import Settings
from gateway.observability.otel_setup import init_otel, shutdown_otel
@pytest.fixture
def otel_gateway_client(monkeypatch):
    monkeypatch.setenv("OTEL_ENABLED", "true")
    shutdown_otel()
    exporter = InMemorySpanExporter()
    init_otel(Settings(), test_exporter=exporter)
    yield TestClient(create_app()), exporter
    shutdown_otel()


def test_proxy_forwards_org_and_traceparent(monkeypatch, tenant_headers, otel_gateway_client):
    headers, org_id = tenant_headers
    client, _exporter = otel_gateway_client
    captured: dict = {}

    class FakeResponse:
        status_code = 201

        def json(self):
            return {"id": "run-otel-1", "status": "pending"}

    async def fake_request(self, method, path, **kwargs):
        captured["method"] = method
        captured["path"] = path
        captured["extra_headers"] = kwargs.get("extra_headers")
        merged = self._merge_headers(kwargs.get("extra_headers"))
        captured["merged_headers"] = merged
        return FakeResponse()

    monkeypatch.setattr(AiceryRuntimeClient, "request", fake_request)

    response = client.post(
        "/v1/runs",
        json={"agent_id": "echo", "input": "hello", "execute": False},
        headers=headers,
    )
    assert response.status_code == 201
    assert captured["extra_headers"]["X-Aicery-Org-Id"] == str(org_id)
    assert "traceparent" in captured["merged_headers"]


def test_gateway_proxy_span_recorded(monkeypatch, tenant_headers, otel_gateway_client):
    headers, org_id = tenant_headers
    client, exporter = otel_gateway_client

    class FakeResponse:
        status_code = 201

        def json(self):
            return {"id": "run-otel-2", "status": "pending"}

    async def fake_request(self, method, path, **kwargs):
        return FakeResponse()

    monkeypatch.setattr(AiceryRuntimeClient, "request", fake_request)

    response = client.post(
        "/v1/runs",
        json={"agent_id": "echo", "input": "hi", "execute": False},
        headers=headers,
    )
    assert response.status_code == 201

    spans = exporter.get_finished_spans()
    proxy_spans = [s for s in spans if s.name == "gateway.proxy"]
    assert proxy_spans
    assert proxy_spans[0].attributes.get("aicery.org_id") == str(org_id)
    assert proxy_spans[0].attributes.get("http.route") == "/v1/runs"
