"""
F1 release gate — MVP_TEAMS_PHASES § Faz 1 çıkış kapısı.

Önkoşullar (bu test çalışmadan önce):
- make up (Postgres + NATS + API, migration 002+)
- WORKSPACE_ROOT içinde README.md (Docker: /app/README.md)
"""

from pathlib import Path

import httpx
import pytest
from tests.integration.conftest import poll_run_until_terminal

pytestmark = pytest.mark.integration


def test_f1_exit_gate_research_run(api_client: httpx.Client) -> None:
    """T1 çıkış: research + read_file → completed, tool_calls >= 1, lifecycle events >= 2."""
    if not Path("README.md").is_file():
        # Docker API uses /app/README.md; host integration may run from repo root
        health = api_client.get("/health")
        if health.status_code != 200:
            pytest.skip("API not reachable")

    response = api_client.post(
        "/v1/runs",
        json={
            "agent_id": "research",
            "input": "Read README.md and summarize",
            "execute": True,
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    run_id = body["id"]

    terminal = poll_run_until_terminal(api_client, run_id, timeout_sec=120)

    assert terminal["status"] == "completed", terminal
    assert terminal.get("tool_calls_count", 0) >= 1, terminal
    assert terminal.get("output_text"), "expected non-empty summary"

    # F1 lifecycle events: run.started + run.completed (tool.called → F2)
    assert terminal.get("events_count", 0) >= 2, (
        "expected at least run.started and run.completed on NATS"
    )
