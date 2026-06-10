"""HITL graph interrupt with Postgres LangGraph checkpointer (integration)."""

from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path

import httpx
import pytest

pytestmark = [pytest.mark.integration, pytest.mark.hitl_postgres]

DEFAULT_BASE = "http://localhost:8000"
DEFAULT_API_KEY = "dev"
DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql+psycopg://aicery:aicery@localhost:5433/aicery"
)
REPO_ROOT = Path(__file__).resolve().parents[2]
COMPOSE_FILE = os.environ.get(
    "AICERY_COMPOSE_FILE", str(REPO_ROOT / "deploy" / "docker-compose.yml")
)


def _api_reachable() -> bool:
    try:
        with httpx.Client(timeout=2.0) as client:
            return client.get(f"{DEFAULT_BASE}/health").is_success
    except httpx.HTTPError:
        return False


def _checkpoint_count(thread_id: str) -> int:
    try:
        import psycopg
    except ImportError:
        pytest.skip("psycopg not installed")
    conn_str = DATABASE_URL.replace("postgresql+psycopg://", "postgresql://")
    try:
        with psycopg.connect(conn_str, connect_timeout=3) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT COUNT(*) FROM checkpoints WHERE thread_id = %s",
                    (thread_id,),
                )
                row = cur.fetchone()
                return int(row[0]) if row else 0
    except Exception as exc:
        pytest.skip(f"Postgres checkpoint DB unavailable: {exc}")


@pytest.fixture
def hitl_client() -> httpx.Client:
    if not _api_reachable():
        pytest.skip("API not reachable — run gate-hitl-postgres or make up")
    key = os.environ.get("AICERY_API_KEY", DEFAULT_API_KEY)
    with httpx.Client(
        base_url=os.environ.get("AICERY_API_URL", DEFAULT_BASE),
        headers={"X-API-Key": key},
        timeout=60.0,
    ) as client:
        yield client


def _poll_status(client: httpx.Client, run_id: str, expected: str, timeout: float = 90.0) -> dict:
    deadline = time.monotonic() + timeout
    last: dict | None = None
    while time.monotonic() < deadline:
        response = client.get(f"/v1/runs/{run_id}")
        response.raise_for_status()
        last = response.json()
        if last.get("status") == expected:
            return last
        terminal = ("completed", "failed", "cancelled")
        if last.get("status") in terminal and expected != last.get("status"):
            break
        time.sleep(0.3)
    raise AssertionError(f"Run {run_id} did not reach {expected}: {last}")


def test_hitl_demo_postgres_checkpoint_suspend_and_resume(hitl_client: httpx.Client) -> None:
    created = hitl_client.post(
        "/v1/runs",
        json={
            "agent_id": "hitl-demo",
            "input": "postgres checkpoint probe",
            "execute": True,
        },
    )
    created.raise_for_status()
    run_id = created.json()["id"]

    suspended = _poll_status(hitl_client, run_id, "suspended")
    assert suspended["status"] == "suspended"

    checkpoint_rows = _checkpoint_count(run_id)
    if checkpoint_rows < 1:
        pytest.skip(
            "No checkpoint rows — ensure API runs with "
            "LANGGRAPH_CHECKPOINT_BACKEND=postgres and HITL_ENABLED=true"
        )

    resume = hitl_client.post(
        f"/v1/runs/{run_id}/resume",
        json={"decision": "approve"},
    )
    resume.raise_for_status()

    completed = _poll_status(hitl_client, run_id, "completed")
    assert completed["status"] == "completed"


def _restart_api_container() -> None:
    result = subprocess.run(
        ["docker", "compose", "-f", COMPOSE_FILE, "restart", "api"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    if result.returncode != 0:
        pytest.skip(f"docker compose restart api failed: {result.stderr or result.stdout}")


def _wait_api_healthy(timeout: float = 90.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if _api_reachable():
            return
        time.sleep(1.0)
    pytest.fail("API did not become healthy after restart")


def test_hitl_demo_postgres_restart_and_resume(hitl_client: httpx.Client) -> None:
    created = hitl_client.post(
        "/v1/runs",
        json={
            "agent_id": "hitl-demo",
            "input": "postgres restart probe",
            "execute": True,
        },
    )
    created.raise_for_status()
    run_id = created.json()["id"]

    suspended = _poll_status(hitl_client, run_id, "suspended")
    assert suspended["status"] == "suspended"

    checkpoint_rows = _checkpoint_count(run_id)
    if checkpoint_rows < 1:
        pytest.skip(
            "No checkpoint rows — ensure API runs with "
            "LANGGRAPH_CHECKPOINT_BACKEND=postgres and HITL_ENABLED=true"
        )

    _restart_api_container()
    _wait_api_healthy()

    assert _poll_status(hitl_client, run_id, "suspended")["status"] == "suspended"

    resume = hitl_client.post(
        f"/v1/runs/{run_id}/resume",
        json={"decision": "approve"},
    )
    resume.raise_for_status()

    completed = _poll_status(hitl_client, run_id, "completed", timeout=120.0)
    assert completed["status"] == "completed"
