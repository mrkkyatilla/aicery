"""T2-E6-01 — 20 concurrent research-chain runs, all terminal."""

import asyncio
import os
import time

import httpx
import pytest

pytestmark = pytest.mark.load

BASE = os.environ.get("AICERY_API_URL", "http://localhost:8000")
HEADERS = {"X-API-Key": os.environ.get("AICERY_API_KEY", "dev")}
PIPELINE = "research-chain"
CONCURRENCY = 20
TIMEOUT_SEC = 300


async def _create_and_poll(client: httpx.AsyncClient, index: int) -> dict:
    response = await client.post(
        "/v1/runs",
        json={
            "pipeline": PIPELINE,
            "input": f"Summarize README.md (job {index})",
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
        await asyncio.sleep(0.3)
    raise TimeoutError(f"pipeline run {run_id} hung")


@pytest.mark.asyncio
async def test_20_concurrent_chains() -> None:
    async with httpx.AsyncClient(base_url=BASE, headers=HEADERS, timeout=60.0) as client:
        health = await client.get("/health")
        if health.status_code != 200:
            pytest.skip("API not running — start with: make up")

        started = time.monotonic()
        results = await asyncio.gather(
            *[_create_and_poll(client, i) for i in range(CONCURRENCY)],
            return_exceptions=True,
        )
        elapsed = time.monotonic() - started

    errors = [r for r in results if isinstance(r, BaseException)]
    terminals = [r for r in results if isinstance(r, dict)]

    assert len(results) == CONCURRENCY
    assert len(errors) / CONCURRENCY < 0.05, f"infra errors: {errors[:3]}"
    assert len(terminals) == CONCURRENCY - len(errors)
    assert all(r["status"] in ("completed", "failed", "cancelled") for r in terminals)
    assert all(r["status"] == "completed" for r in terminals), [
        r["status"] for r in terminals if r["status"] != "completed"
    ]
    assert elapsed < TIMEOUT_SEC, f"expected < {TIMEOUT_SEC}s, took {elapsed:.1f}s"
