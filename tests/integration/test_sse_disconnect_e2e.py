"""SSE client disconnect cancels an in-flight run (integration)."""

from __future__ import annotations

import subprocess
import time

import httpx
import pytest
from tests.integration.conftest import poll_run_until_terminal

pytestmark = [pytest.mark.integration, pytest.mark.sse_e2e]


def test_sse_disconnect_cancels_run_integration(
    api_client: httpx.Client,
    api_base_url: str,
    api_headers: dict[str, str],
) -> None:
    created = api_client.post(
        "/v1/runs",
        json={
            "agent_id": "echo",
            "input": "__slow__:disconnect-e2e",
            "execute": True,
        },
    )
    created.raise_for_status()
    run_id = created.json()["id"]

    status = api_client.get(f"/v1/runs/{run_id}").json()["status"]
    if status in ("completed", "failed", "cancelled"):
        pytest.skip("run finished before stream could attach")

    api_key = api_headers.get("X-API-Key", "dev")
    stream_url = f"{api_base_url.rstrip('/')}/v1/runs/{run_id}/stream"
    proc = subprocess.Popen(
        ["curl", "-sN", stream_url, "-H", f"X-API-Key: {api_key}"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        time.sleep(1.0)
        proc.terminate()
        proc.wait(timeout=10)
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait(timeout=5)

    terminal = poll_run_until_terminal(api_client, run_id, timeout_sec=15.0)
    assert terminal["status"] == "cancelled"
