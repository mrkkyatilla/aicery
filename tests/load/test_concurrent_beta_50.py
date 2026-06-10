"""T3-E6-01 — 50 concurrent echo runs, 10 min wall clock, all terminal, no zombies."""

from __future__ import annotations

import asyncio
import os
import time

import httpx
import pytest
from tests.load.load_utils import TERMINAL_STATUSES, create_and_poll

pytestmark = pytest.mark.load

BASE = os.environ.get("AICERY_API_URL", "http://localhost:8000")
HEADERS = {"X-API-Key": os.environ.get("AICERY_API_KEY", "dev")}
CONCURRENCY = int(os.environ.get("BETA_LOAD_CONCURRENCY", "50"))
WALL_CLOCK_SEC = int(os.environ.get("BETA_LOAD_WALL_SEC", "600"))
PER_RUN_TIMEOUT_SEC = float(os.environ.get("BETA_LOAD_PER_RUN_SEC", "120"))
MAX_INFRA_ERROR_RATIO = float(os.environ.get("BETA_LOAD_MAX_ERROR_RATIO", "0.02"))
AGENT_ID = os.environ.get("BETA_LOAD_AGENT", "echo")


async def _run_one(client: httpx.AsyncClient, index: int) -> dict:
    return await create_and_poll(
        client,
        payload={
            "agent_id": AGENT_ID,
            "input": f"beta-load-{index}",
            "execute": True,
        },
        per_run_timeout_sec=PER_RUN_TIMEOUT_SEC,
    )


@pytest.mark.asyncio
async def test_50_concurrent_beta_load() -> None:
    async with httpx.AsyncClient(base_url=BASE, headers=HEADERS, timeout=60.0) as client:
        health = await client.get("/health")
        if health.status_code != 200:
            pytest.skip("API not running — start with: make up")

        started = time.monotonic()
        results = await asyncio.gather(
            *[_run_one(client, i) for i in range(CONCURRENCY)],
            return_exceptions=True,
        )
        elapsed = time.monotonic() - started

    errors = [r for r in results if isinstance(r, BaseException)]
    terminals = [r for r in results if isinstance(r, dict)]
    rate_limited = [
        e
        for e in errors
        if isinstance(e, httpx.HTTPStatusError) and e.response.status_code == 429
    ]

    assert len(results) == CONCURRENCY, "unexpected result count"
    if rate_limited:
        pytest.fail(
            f"{len(rate_limited)} requests rate-limited (429). "
            "Restart API with RATE_LIMIT_ENABLED=false for beta load."
        )
    assert len(errors) / CONCURRENCY <= MAX_INFRA_ERROR_RATIO, (
        f"infra errors ({len(errors)}/{CONCURRENCY}): {errors[:3]}"
    )
    assert len(terminals) + len(errors) == CONCURRENCY
    assert all(r["status"] in TERMINAL_STATUSES for r in terminals)
    hung = [r for r in errors if isinstance(r, TimeoutError)]
    assert not hung, f"zombie runs: {hung}"
    failed = [r for r in terminals if r["status"] != "completed"]
    assert not failed, f"non-completed runs: {[r['status'] for r in failed[:5]]}"
    assert elapsed < WALL_CLOCK_SEC, (
        f"wall clock {elapsed:.1f}s exceeded {WALL_CLOCK_SEC}s (T3-E6-01)"
    )
