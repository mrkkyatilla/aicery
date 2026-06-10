import time

import pytest
from fastapi.testclient import TestClient
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from runtime.adapters.db import session as session_mod
from runtime.adapters.db.models import Base
from runtime.adapters.events.emitter import RunEventEmitter
from runtime.adapters.events.factory import reset_event_publisher, set_test_publisher
from runtime.adapters.events.memory_publisher import InMemoryEventPublisher
from runtime.adapters.langgraph_orchestrator import LangGraphOrchestrator
from runtime.adapters.providers.mock import MockProvider
from runtime.api import deps as deps_mod
from runtime.api.app import create_app
from runtime.api.deps import _get_emitter
from runtime.config import Settings
from runtime.observability.otel_setup import get_test_exporter, init_otel, shutdown_otel


@pytest.fixture
def otel_trace_client(monkeypatch):
    monkeypatch.setenv("API_KEY", "dev")
    monkeypatch.setenv("USE_MOCK_PROVIDER", "true")
    monkeypatch.setenv("DATABASE_URL", "sqlite://")
    monkeypatch.setenv("NATS_ENABLED", "false")
    monkeypatch.setenv("OTEL_ENABLED", "true")

    shutdown_otel()
    exporter = InMemorySpanExporter()
    init_otel(Settings(), test_exporter=exporter)

    session_mod._engine = None
    session_mod._SessionLocal = None
    engine = session_mod.get_engine("sqlite://")
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

    publisher = InMemoryEventPublisher()
    set_test_publisher(publisher)
    app = create_app()

    async def override_emitter():
        return RunEventEmitter(publisher)

    app.dependency_overrides[_get_emitter] = override_emitter
    deps_mod._orchestrator = LangGraphOrchestrator(provider=MockProvider())

    with TestClient(app) as test_client:
        yield test_client, exporter

    set_test_publisher(None)
    reset_event_publisher()
    shutdown_otel()


@pytest.fixture
def trace_client_no_otel(monkeypatch):
    monkeypatch.setenv("API_KEY", "dev")
    monkeypatch.setenv("USE_MOCK_PROVIDER", "true")
    monkeypatch.setenv("DATABASE_URL", "sqlite://")
    monkeypatch.setenv("NATS_ENABLED", "false")
    monkeypatch.setenv("OTEL_ENABLED", "false")

    shutdown_otel()
    init_otel(Settings())

    session_mod._engine = None
    session_mod._SessionLocal = None
    engine = session_mod.get_engine("sqlite://")
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

    publisher = InMemoryEventPublisher()
    set_test_publisher(publisher)
    app = create_app()

    async def override_emitter():
        return RunEventEmitter(publisher)

    app.dependency_overrides[_get_emitter] = override_emitter
    deps_mod._orchestrator = LangGraphOrchestrator(provider=MockProvider())

    with TestClient(app) as test_client:
        yield test_client
    set_test_publisher(None)
    reset_event_publisher()
    shutdown_otel()


def test_otel_disabled_exports_no_spans(trace_client_no_otel) -> None:
    headers = {"X-API-Key": "dev"}
    created = trace_client_no_otel.post(
        "/v1/runs",
        json={"agent_id": "echo", "input": "no-otel", "execute": True},
        headers=headers,
    )
    assert created.status_code == 201
    run_id = created.json()["id"]
    for _ in range(60):
        body = trace_client_no_otel.get(f"/v1/runs/{run_id}", headers=headers).json()
        if body["status"] in ("completed", "failed"):
            break
        time.sleep(0.1)

    exporter = get_test_exporter()
    assert exporter is None or len(exporter.get_finished_spans()) == 0


def test_otel_echo_run_exports_run_and_llm_spans(otel_trace_client) -> None:
    client, exporter = otel_trace_client
    headers = {"X-API-Key": "dev", "X-Aicery-Org-Id": "org-123"}
    created = client.post(
        "/v1/runs",
        json={"agent_id": "echo", "input": "otel-me", "execute": True},
        headers=headers,
    )
    assert created.status_code == 201
    run_id = created.json()["id"]

    for _ in range(60):
        body = client.get(f"/v1/runs/{run_id}", headers=headers).json()
        if body["status"] in ("completed", "failed"):
            break
        time.sleep(0.1)

    spans = exporter.get_finished_spans()
    names = {s.name for s in spans}
    assert "aicery.run" in names
    assert "aicery.llm" in names or "aicery.agent.step" in names

    run_spans = [s for s in spans if s.name == "aicery.run"]
    assert run_spans[0].attributes.get("aicery.run_id") == run_id
    assert run_spans[0].attributes.get("aicery.org_id") == "org-123"

    trace = client.get(f"/v1/runs/{run_id}/trace", headers=headers)
    assert trace.status_code == 200
    assert len(trace.json()["steps"]) >= 2


def test_otel_parent_child_when_parent_step_id_present() -> None:
    from core.domain.run import Run, RunStatus
    from core.domain.trace import TraceStep, TraceStepType
    from runtime.observability.otel_setup import init_otel, shutdown_otel
    from runtime.observability.run_context import RunOtelContext

    shutdown_otel()
    exporter = InMemorySpanExporter()
    init_otel(Settings(otel_enabled=True), test_exporter=exporter)

    run = Run(id="run-1", agent_id="echo", input_text="hi", status=RunStatus.RUNNING)
    ctx = RunOtelContext(run)
    from opentelemetry import trace

    tracer = trace.get_tracer("test")
    with tracer.start_as_current_span("aicery.run") as root:
        ctx.root_span = root
        parent = TraceStep(
            run_id="run-1",
            type=TraceStepType.AGENT,
            name="parent",
            step_id="step-parent",
        )
        child = TraceStep(
            run_id="run-1",
            type=TraceStepType.LLM,
            name="child",
            step_id="step-child",
            parent_step_id="step-parent",
        )
        ctx.export_step(parent)
        ctx.export_step(child)

    spans = exporter.get_finished_spans()
    parent_span = next((s for s in spans if s.name == "aicery.agent.step"), None)
    child_span = next((s for s in spans if s.name == "aicery.llm"), None)
    assert parent_span is not None
    assert child_span is not None
    assert child_span.parent.span_id == parent_span.context.span_id

    shutdown_otel()
