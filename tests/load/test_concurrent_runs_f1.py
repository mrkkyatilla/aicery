"""T1-E6-01 — 10 concurrent runs, all terminal, no hung runs."""

import asyncio
import os
import time

import httpx
import pytest

pytestmark = pytest.mark.load

BASE = os.environ.get("AICERY_API_URL", "http://localhost:8000")
HEADERS = {"X-API-Key": os.environ.get("AICERY_API_KEY", "dev")}
CONCURRENCY = 10
TIMEOUT_SEC = 120


async def _create_and_poll(client: httpx.AsyncClient, index: int) -> dict:
    response = await client.post(
        "/v1/runs",
        json={"agent_id": "echo", "input": f"concurrent-{index}", "execute": True},
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
async def test_10_concurrent_runs() -> None:
    started = time.monotonic()
    async with httpx.AsyncClient(base_url=BASE, headers=HEADERS, timeout=30.0) as client:
        results = await asyncio.gather(
            *[_create_and_poll(client, i) for i in range(CONCURRENCY)]
        )
    elapsed = time.monotonic() - started

    assert len(results) == CONCURRENCY
    assert all(r["status"] in ("completed", "failed") for r in results)
    assert all(r["status"] == "completed" for r in results), results
    assert elapsed < 120, f"expected < 2 min, took {elapsed:.1f}s"
