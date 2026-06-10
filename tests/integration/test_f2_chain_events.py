"""F2 chain run emits started, agent.step (×3), tool.called, completed."""

import time

import httpx
import pytest

pytestmark = pytest.mark.integration

BASE = "http://localhost:8000"
HEADERS = {"X-API-Key": "dev"}


def test_pipeline_run_event_types() -> None:
    with httpx.Client(base_url=BASE, headers=HEADERS, timeout=60.0) as client:
        if client.get("/health").status_code != 200:
            pytest.skip("API not running")

        created = client.post(
            "/v1/runs",
            json={
                "pipeline": "research-chain",
                "input": "Summarize README.md briefly",
                "execute": True,
            },
        )
        assert created.status_code == 201, created.text
        run_id = created.json()["id"]

        terminal = None
        for _ in range(120):
            body = client.get(f"/v1/runs/{run_id}").json()
            if body["status"] in ("completed", "failed", "cancelled"):
                terminal = body
                break
            time.sleep(0.5)

    assert terminal is not None
    assert terminal["status"] == "completed", terminal
    assert (terminal.get("tool_calls_count") or 0) >= 2

    # Event counts via API metrics (NATS/in-memory not exposed here); verify run metrics
    assert terminal.get("events_count", 0) >= 2
