"""T1-E1-02b — NATS delivers run lifecycle events for executed runs."""

import asyncio
import json
import os

import httpx
import pytest

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

TERMINAL = frozenset({"completed", "failed", "cancelled"})


@pytest.mark.asyncio
async def test_nats_run_completed_delivered() -> None:
    import nats

    base = os.environ.get("AICERY_API_URL", "http://localhost:8000")
    headers = {"X-API-Key": os.environ.get("AICERY_API_KEY", "dev")}
    nats_url = os.environ.get("NATS_URL", "nats://localhost:4223")
    received: list[dict] = []

    nc = await nats.connect(nats_url)
    sub = await nc.subscribe("aicery.events.v1.>")

    async def _reader():
        while True:
            try:
                msg = await sub.next_msg(timeout=0.5)
            except TimeoutError:
                continue
            except Exception:
                continue
            received.append(json.loads(msg.data.decode()))

    reader = asyncio.create_task(_reader())

    try:
        async with httpx.AsyncClient(base_url=base, headers=headers, timeout=30.0) as client:
            response = await client.post(
                "/v1/runs",
                json={"agent_id": "echo", "input": "ping", "execute": True},
            )
            assert response.status_code == 201
            run_id = response.json()["id"]

            terminal = None
            for _ in range(240):
                get_resp = await client.get(f"/v1/runs/{run_id}")
                terminal = get_resp.json()
                if terminal["status"] in TERMINAL:
                    break
                await asyncio.sleep(0.25)

            assert terminal is not None
            assert terminal["status"] == "completed"
            assert terminal.get("events_count", 0) >= 2

        await asyncio.sleep(1.0)
    finally:
        reader.cancel()
        try:
            await reader
        except asyncio.CancelledError:
            pass
        await nc.drain()

    run_events = [e for e in received if e.get("run_id") == run_id]
    subjects = {e["subject"] for e in run_events}
    assert "aicery.events.v1.run.completed" in subjects
    assert "aicery.events.v1.run.started" in subjects
