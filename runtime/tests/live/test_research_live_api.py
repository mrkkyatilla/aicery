"""Live API: research agent with real Gemini (requires make up + GEMINI_API_KEY)."""

from __future__ import annotations

import os
import time
from pathlib import Path

import httpx
import pytest

from runtime.config import Settings

pytestmark = pytest.mark.live

BASE = os.environ.get("AICERY_API_URL", "http://localhost:8000")


def _require_key() -> None:
    if not os.environ.get("GEMINI_API_KEY", "").strip():
        pytest.skip("GEMINI_API_KEY not set")


def _require_readme() -> None:
    readme = Path(Settings().workspace_root).resolve() / "README.md"
    if not readme.is_file():
        pytest.skip("README.md missing in workspace_root for research live test")


def test_live_research_run_via_api() -> None:
    _require_key()
    _require_readme()
    headers = {"X-API-Key": os.environ.get("AICERY_API_KEY", "dev")}
    with httpx.Client(base_url=BASE, timeout=120.0) as client:
        health = client.get("/health")
        if health.status_code != 200:
            pytest.skip("API not running — start with: make up && USE_MOCK_PROVIDER=false")

        created = client.post(
            "/v1/runs",
            json={
                "agent_id": "research",
                "input": "Summarize README.md in two sentences.",
                "execute": True,
            },
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
    output = terminal.get("output_text") or ""
    assert output
    assert "echo:" not in output.lower()
    assert (terminal.get("tool_calls_count") or 0) >= 1
    assert any(word in output.lower() for word in ("aicery", "agent", "runtime", "motor"))
