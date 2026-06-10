"""T2-E2-02: SSE disconnect / cancel → run cancelled."""

from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncIterator
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from core.domain.run import Run, RunStatus
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
from runtime.api.routes import stream as stream_module
from runtime.config import Settings
from runtime.services.run_execution import get_run_execution, register_run, request_cancel
from runtime.services.run_service import RunService


class SlowMockProvider(MockProvider):
    async def stream(self, messages: list[dict], **kwargs) -> AsyncIterator[str]:
        await asyncio.sleep(3.0)
        yield "slow-chunk"


@pytest.fixture
def disconnect_client(monkeypatch):
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
    deps_mod._orchestrator = LangGraphOrchestrator(provider=SlowMockProvider())

    def slow_build(replay_ctx, *, session=None, trace_recorder=None):
        return LangGraphOrchestrator(
            provider=SlowMockProvider(),
            replay_ctx=replay_ctx,
            trace_recorder=trace_recorder,
            trace_session=session,
        )

    monkeypatch.setattr(
        "runtime.services.run_service.build_orchestrator",
        slow_build,
    )

    with TestClient(app) as test_client:
        yield test_client, publisher
    set_test_publisher(None)
    reset_event_publisher()


@pytest.mark.asyncio
async def test_cancel_run_while_executing(disconnect_client) -> None:
    """cancel_run stops an in-flight execute (same path as SSE disconnect)."""
    test_client, publisher = disconnect_client
    headers = {"X-API-Key": "dev"}
    created = test_client.post(
        "/v1/runs",
        json={"agent_id": "echo", "input": "cancel-me", "execute": True},
        headers=headers,
    )
    run_id = created.json()["id"]
    assert get_run_execution(run_id) is not None, "run execution registry missing"

    from runtime.adapters.db.session import get_session_factory

    session = get_session_factory()()
    try:
        emitter = RunEventEmitter(publisher)
        service = RunService(session, deps_mod._orchestrator, emitter, Settings())
        await service.cancel_run(run_id)
    finally:
        session.close()

    terminal = None
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        body = test_client.get(f"/v1/runs/{run_id}", headers=headers).json()
        if body["status"] == "cancelled":
            terminal = body
            break
        await asyncio.sleep(0.2)

    assert terminal is not None, "run was not cancelled within 10s"
    assert terminal["status"] == "cancelled"


@pytest.mark.asyncio
async def test_sse_generator_disconnect_invokes_cancel(disconnect_client) -> None:
    """Stream handler calls cancel_run when the client disconnects."""
    _test_client, publisher = disconnect_client
    run_id = "550e8400-e29b-41d4-a716-446655440001"
    state = register_run(run_id)
    state.history.append({"type": "token", "text": "x"})

    request = MagicMock()
    request.receive = AsyncMock(return_value={"type": "http.disconnect"})

    cancelled_run = Run(
        id=run_id,
        agent_id="echo",
        input_text="",
        status=RunStatus.CANCELLED,
    )

    async def _cancel_and_flag(rid: str) -> Run:
        request_cancel(rid)
        return cancelled_run

    service = MagicMock()
    service.cancel_run = AsyncMock(side_effect=_cancel_and_flag)

    emitter = RunEventEmitter(publisher)
    real_service = RunService(
        MagicMock(),
        deps_mod._orchestrator,
        emitter,
        Settings(),
    )
    real_service.cancel_run = service.cancel_run  # type: ignore[method-assign]

    events = []
    async for event in stream_module._sse_generator(run_id, real_service, request):
        events.append(event)

    service.cancel_run.assert_awaited_once_with(run_id)
