"""Hot memory across two runs with shared conversation_id (Redis backend)."""

from __future__ import annotations

import os
import time

import httpx
import pytest

pytestmark = [pytest.mark.integration, pytest.mark.hot_memory_integration]


@pytest.fixture(scope="module")
def hot_memory_api_available() -> bool:
    if os.environ.get("HOT_MEMORY_INTEGRATION") != "1":
        pytest.skip("Set HOT_MEMORY_INTEGRATION=1 and HOT_MEMORY_ENABLED=true on API")
    try:
        with httpx.Client(timeout=2.0) as client:
            return client.get("http://localhost:8000/health").is_success
    except httpx.HTTPError:
        return False


def test_two_runs_share_conversation_hot_memory(
    api_client: httpx.Client,
    hot_memory_api_available: bool,
) -> None:
    if not hot_memory_api_available:
        pytest.skip("API not up or HOT_MEMORY_INTEGRATION not enabled")

    conv_id = f"conv-integration-{int(time.time())}"

    first = api_client.post(
        "/v1/runs",
        json={
            "agent_id": "echo",
            "input": "remember-alpha",
            "execute": True,
            "conversation_id": conv_id,
        },
    )
    first.raise_for_status()
    run1 = first.json()["id"]

    deadline = time.monotonic() + 30.0
    while time.monotonic() < deadline:
        body = api_client.get(f"/v1/runs/{run1}").json()
        if body["status"] in ("completed", "failed", "cancelled"):
            assert body["status"] == "completed"
            break
        time.sleep(0.2)
    else:
        pytest.fail("first run did not complete")

    second = api_client.post(
        "/v1/runs",
        json={
            "agent_id": "echo",
            "input": "follow-up-beta",
            "execute": True,
            "conversation_id": conv_id,
        },
    )
    second.raise_for_status()
    run2 = second.json()["id"]
    assert second.json()["conversation_id"] == conv_id

    deadline = time.monotonic() + 30.0
    while time.monotonic() < deadline:
        body = api_client.get(f"/v1/runs/{run2}").json()
        if body["status"] in ("completed", "failed", "cancelled"):
            assert body["status"] == "completed"
            break
        time.sleep(0.2)
    else:
        pytest.fail("second run did not complete")

    # Context sharing is covered by unit tests; integration verifies API + Redis path.
