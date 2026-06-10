"""Shared helpers for load tests (T3-E6-01)."""

from __future__ import annotations

import asyncio
import time

import httpx

TERMINAL_STATUSES = frozenset({"completed", "failed", "cancelled"})


def stream_first_token_ms(client: httpx.Client, run_id: str, *, timeout: float = 30.0) -> float:
    """Milliseconds until first SSE token event for a run stream."""
    started = time.perf_counter()
    event_type: str | None = None
    with client.stream("GET", f"/v1/runs/{run_id}/stream", timeout=timeout) as resp:
        resp.raise_for_status()
        for line in resp.iter_lines():
            if not line:
                continue
            if line.startswith("event:"):
                event_type = line[6:].strip()
            elif line.startswith("data:") and event_type == "token":
                return (time.perf_counter() - started) * 1000.0
    raise AssertionError(f"no token event in stream for run {run_id}")


async def create_and_poll(
    client: httpx.AsyncClient,
    *,
    payload: dict,
    per_run_timeout_sec: float,
    poll_interval_sec: float = 0.25,
) -> dict:
    response = await client.post("/v1/runs", json=payload)
    response.raise_for_status()
    run_id = response.json()["id"]
    deadline = time.monotonic() + per_run_timeout_sec
    while time.monotonic() < deadline:
        get_resp = await client.get(f"/v1/runs/{run_id}")
        get_resp.raise_for_status()
        data = get_resp.json()
        if data["status"] in TERMINAL_STATUSES:
            return data
        await asyncio.sleep(poll_interval_sec)
    raise TimeoutError(f"run {run_id} hung after {per_run_timeout_sec}s")
