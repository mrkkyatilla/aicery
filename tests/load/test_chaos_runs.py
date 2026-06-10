"""T2-E6-02 — chaos tool failures: all runs reach terminal state."""

import asyncio
import os
import time

import httpx
import pytest

pytestmark = pytest.mark.load

BASE = os.environ.get("AICERY_API_URL", "http://localhost:8000")
HEADERS = {"X-API-Key": os.environ.get("AICERY_API_KEY", "dev")}
CONCURRENCY = 5
TIMEOUT_SEC = 120


async def _create_and_poll(client: httpx.AsyncClient, index: int) -> dict:
    response = await client.post(
        "/v1/runs",
        json={
            "agent_id": "research",
            "input": f"Summarize README.md chaos-{index}",
            "execute": True,
        },
    )
    response.raise_for_status()
    run_id = response.json()["id"]
    deadline = time.monotonic() + TIMEOUT_SEC
    while time.monotonic() < deadline:
        get_resp = await client.get(f"/v1/runs/{run_id}")
        get_resp.raise_for_status()
        data = get_resp.json()
        if data["status"] in ("completed", "failed", "cancelled"):
            return data
        await asyncio.sleep(0.2)
    raise TimeoutError(f"run {run_id} hung")


@pytest.mark.asyncio
async def test_chaos_runs_all_terminal() -> None:
    if not os.environ.get("CHAOS_TOOL_FAIL_RATE"):
        pytest.skip("Set CHAOS_TOOL_FAIL_RATE=0.3 and restart API")

    async with httpx.AsyncClient(base_url=BASE, headers=HEADERS, timeout=60.0) as client:
        health = await client.get("/health")
        if health.status_code != 200:
            pytest.skip("API not running — CHAOS_TOOL_FAIL_RATE requires make up with env")

        results = await asyncio.gather(
            *[_create_and_poll(client, i) for i in range(CONCURRENCY)],
            return_exceptions=True,
        )

    hung = [r for r in results if isinstance(r, TimeoutError)]
    terminals = [r for r in results if isinstance(r, dict)]

    assert not hung, f"zombie runs: {hung}"
    assert len(terminals) + len(hung) == CONCURRENCY
    assert all(r["status"] in ("completed", "failed", "cancelled") for r in terminals)
