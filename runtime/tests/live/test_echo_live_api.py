"""Live API: echo agent end-to-end with real Gemini (requires make up + GEMINI_API_KEY)."""

import os
import time

import httpx
import pytest

pytestmark = pytest.mark.live

BASE = os.environ.get("AICERY_API_URL", "http://localhost:8000")


def _require_key() -> None:
    if not os.environ.get("GEMINI_API_KEY", "").strip():
        pytest.skip("GEMINI_API_KEY not set")


def test_live_echo_run_via_api() -> None:
    _require_key()
    headers = {"X-API-Key": os.environ.get("AICERY_API_KEY", "dev")}
    with httpx.Client(base_url=BASE, timeout=60.0) as client:
        health = client.get("/health")
        if health.status_code != 200:
            pytest.skip("API not running — start with: make up")

        created = client.post(
            "/v1/runs",
            json={"agent_id": "echo", "input": "Say hi in 3 words.", "execute": True},
            headers=headers,
        )
        assert created.status_code == 201, created.text
        run_id = created.json()["id"]

        terminal = None
        for _ in range(120):
            body = client.get(f"/v1/runs/{run_id}", headers=headers).json()
            if body["status"] in ("completed", "failed", "cancelled"):
                terminal = body
                break
            time.sleep(0.5)

    assert terminal is not None
    assert terminal["status"] == "completed", terminal
    assert terminal.get("output_text")
    assert "echo:" not in (terminal["output_text"] or "").lower()
