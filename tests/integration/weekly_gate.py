"""
E6 Cuma gate — F1 kritik path subset.

Çalıştırma:
  make up && pytest tests/integration/weekly_gate.py -m integration
"""

import httpx
import pytest
from tests.integration.conftest import poll_run_until_terminal

pytestmark = pytest.mark.integration


def test_gate_health(api_client: httpx.Client) -> None:
    assert api_client.get("/health").json()["status"] == "ok"


def test_gate_echo_lifecycle(api_client: httpx.Client) -> None:
    created = api_client.post(
        "/v1/runs",
        json={"agent_id": "echo", "input": "gate", "execute": True},
    )
    assert created.status_code == 201
    terminal = poll_run_until_terminal(api_client, created.json()["id"], timeout_sec=60)
    assert terminal["status"] == "completed"


def test_gate_auth_rejects_invalid_key(api_base_url: str) -> None:
    with httpx.Client(base_url=api_base_url, timeout=10.0) as client:
        response = client.post(
            "/v1/runs",
            json={"agent_id": "echo", "input": "x", "execute": False},
            headers={"X-API-Key": "invalid-key"},
        )
    assert response.status_code == 401
