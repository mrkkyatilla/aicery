import json
import time

import pytest
from fastapi.testclient import TestClient

from runtime.adapters.db import session as session_mod
from runtime.adapters.db.models import Base
from runtime.adapters.events.emitter import RunEventEmitter
from runtime.adapters.events.memory_publisher import InMemoryEventPublisher
from runtime.adapters.langgraph_orchestrator import LangGraphOrchestrator
from runtime.adapters.providers.mock import MockProvider
from runtime.api import deps as deps_mod
from runtime.api.app import create_app
from runtime.api.deps import _get_emitter


@pytest.fixture
def sse_client(monkeypatch):
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
    app = create_app()

    async def override_emitter():
        return RunEventEmitter(publisher)

    app.dependency_overrides[_get_emitter] = override_emitter
    deps_mod._orchestrator = LangGraphOrchestrator(provider=MockProvider())

    with TestClient(app) as test_client:
        yield test_client


def _parse_sse_events(body: str) -> list[tuple[str, dict]]:
    events: list[tuple[str, dict]] = []
    current_event: str | None = None
    data_lines: list[str] = []
    for line in body.splitlines():
        if not line:
            if current_event and data_lines:
                events.append((current_event, json.loads("\n".join(data_lines))))
            current_event = None
            data_lines = []
            continue
        if line.startswith("event:"):
            current_event = line[6:].strip()
        elif line.startswith("data:"):
            data_lines.append(line[5:].strip())
    return events


def test_sse_echo_done_after_complete(sse_client: TestClient) -> None:
    headers = {"X-API-Key": "dev"}
    create = sse_client.post(
        "/v1/runs",
        json={"agent_id": "echo", "input": "stream-me", "execute": True},
        headers=headers,
    )
    run_id = create.json()["id"]

    for _ in range(50):
        get_resp = sse_client.get(f"/v1/runs/{run_id}", headers=headers)
        if get_resp.json()["status"] in ("completed", "failed", "cancelled"):
            break
        time.sleep(0.05)

    stream_resp = sse_client.get(
        f"/v1/runs/{run_id}/stream",
        headers={**headers, "Accept": "text/event-stream"},
    )
    assert stream_resp.status_code == 200
    events = _parse_sse_events(stream_resp.text)
    assert any(name == "done" for name, _ in events)


def test_sse_replay_tokens_after_complete(sse_client: TestClient) -> None:
    headers = {"X-API-Key": "dev"}
    create = sse_client.post(
        "/v1/runs",
        json={"agent_id": "echo", "input": "replay-test", "execute": True},
        headers=headers,
    )
    run_id = create.json()["id"]
    terminal = None
    for _ in range(60):
        terminal = sse_client.get(f"/v1/runs/{run_id}", headers=headers).json()
        if terminal["status"] == "completed":
            break
        time.sleep(0.1)
    assert terminal is not None and terminal["status"] == "completed", terminal

    stream_resp = sse_client.get(
        f"/v1/runs/{run_id}/stream",
        headers={**headers, "Accept": "text/event-stream"},
    )
    events = _parse_sse_events(stream_resp.text)
    token_count = sum(1 for name, _ in events if name == "token")
    assert token_count >= 1
    assert any(name == "done" for name, _ in events)
