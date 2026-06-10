import time

import pytest
from fastapi.testclient import TestClient

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


@pytest.fixture
def trace_client(monkeypatch):
    monkeypatch.setenv("API_KEY", "dev")
    monkeypatch.setenv("USE_MOCK_PROVIDER", "true")
    monkeypatch.setenv("DATABASE_URL", "sqlite://")
    monkeypatch.setenv("NATS_ENABLED", "false")

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


def test_echo_run_has_trace(trace_client) -> None:
    headers = {"X-API-Key": "dev"}
    created = trace_client.post(
        "/v1/runs",
        json={"agent_id": "echo", "input": "trace-me", "execute": True},
        headers=headers,
    )
    assert created.status_code == 201
    run_id = created.json()["id"]

    for _ in range(60):
        body = trace_client.get(f"/v1/runs/{run_id}", headers=headers).json()
        if body["status"] in ("completed", "failed"):
            break
        time.sleep(0.1)

    trace = trace_client.get(f"/v1/runs/{run_id}/trace", headers=headers)
    assert trace.status_code == 200
    steps = trace.json()["steps"]
    assert len(steps) >= 2
    types = {s["type"] for s in steps}
    assert "llm" in types


def test_replay_echo_deterministic(trace_client) -> None:
    headers = {"X-API-Key": "dev"}
    created = trace_client.post(
        "/v1/runs",
        json={"agent_id": "echo", "input": "replay-me", "execute": True},
        headers=headers,
    )
    source_id = created.json()["id"]
    for _ in range(60):
        if trace_client.get(f"/v1/runs/{source_id}", headers=headers).json()["status"] == "completed":
            break
        time.sleep(0.1)

    replay_headers = {
        **headers,
        "X-Aicery-Replay-Mode": "replay",
        "X-Aicery-Source-Run-Id": source_id,
        "X-Aicery-Mock-Tools": "true",
    }
    replay = trace_client.post(
        "/v1/runs",
        json={"agent_id": "echo", "input": "replay-me", "execute": True},
        headers=replay_headers,
    )
    assert replay.status_code == 201
    replay_id = replay.json()["id"]
    for _ in range(60):
        body = trace_client.get(f"/v1/runs/{replay_id}", headers=headers).json()
        if body["status"] in ("completed", "failed"):
            assert body["status"] == "completed"
            assert "echo:replay-me" in (body.get("output_text") or "")
            break
        time.sleep(0.1)

    source_steps = trace_client.get(f"/v1/runs/{source_id}/trace", headers=headers).json()["steps"]
    replay_steps = trace_client.get(f"/v1/runs/{replay_id}/trace", headers=headers).json()["steps"]
    source_llm = [s for s in source_steps if s["type"] == "llm"]
    replay_llm = [s for s in replay_steps if s["type"] == "llm"]
    assert source_llm and replay_llm
    assert source_llm[0]["input_hash"] == replay_llm[0]["input_hash"]
    assert source_llm[0]["output_hash"] == replay_llm[0]["output_hash"]


def _step_signatures(steps: list[dict]) -> list[tuple]:
    return [
        (s["type"], s["name"], s["input_hash"], s.get("output_hash"))
        for s in steps
    ]


def _wait_completed(client, run_id: str, headers: dict) -> dict:
    body = {}
    for _ in range(60):
        body = client.get(f"/v1/runs/{run_id}", headers=headers).json()
        if body["status"] in ("completed", "failed", "cancelled"):
            return body
        time.sleep(0.1)
    return body


def test_echo_trace_golden_step_count(trace_client) -> None:
    """T3-E2-01: completed echo run has agent + llm trace steps."""
    headers = {"X-API-Key": "dev"}
    run_id = trace_client.post(
        "/v1/runs",
        json={"agent_id": "echo", "input": "golden", "execute": True},
        headers=headers,
    ).json()["id"]
    _wait_completed(trace_client, run_id, headers)
    steps = trace_client.get(f"/v1/runs/{run_id}/trace", headers=headers).json()["steps"]
    assert len(steps) >= 2
    assert {s["type"] for s in steps} >= {"agent", "llm"}


def test_replay_determinism_two_runs_identical_hashes(trace_client) -> None:
    """T3-E5-01: two replays from same source → identical trace step hashes."""
    headers = {"X-API-Key": "dev"}
    source_id = trace_client.post(
        "/v1/runs",
        json={"agent_id": "echo", "input": "determinism", "execute": True},
        headers=headers,
    ).json()["id"]
    _wait_completed(trace_client, source_id, headers)

    replay_headers = {
        **headers,
        "X-Aicery-Replay-Mode": "replay",
        "X-Aicery-Mock-Tools": "true",
    }

    def _replay() -> list[tuple]:
        h = {
            **replay_headers,
            "X-Aicery-Source-Run-Id": source_id,
        }
        rid = trace_client.post(
            "/v1/runs",
            json={"agent_id": "echo", "input": "determinism", "execute": True},
            headers=h,
        ).json()["id"]
        _wait_completed(trace_client, rid, headers)
        steps = trace_client.get(f"/v1/runs/{rid}/trace", headers=headers).json()["steps"]
        return _step_signatures(steps)

    sig_a = _replay()
    sig_b = _replay()
    assert sig_a == sig_b
    assert len(sig_a) >= 2
