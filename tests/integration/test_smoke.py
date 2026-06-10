import time

import httpx
import pytest

pytestmark = pytest.mark.integration

BASE = "http://localhost:8000"
HEADERS = {"X-API-Key": "dev"}


def test_health_smoke() -> None:
    response = httpx.get(f"{BASE}/health", timeout=10.0)
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_create_run_smoke() -> None:
    response = httpx.post(
        f"{BASE}/v1/runs",
        json={"agent_id": "echo", "input": "hello", "execute": True},
        headers=HEADERS,
        timeout=10.0,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["agent_id"] == "echo"
    run_id = data["id"]

    terminal = None
    for _ in range(60):
        get_resp = httpx.get(f"{BASE}/v1/runs/{run_id}", headers=HEADERS, timeout=10.0)
        assert get_resp.status_code == 200
        terminal = get_resp.json()
        if terminal["status"] in ("completed", "failed"):
            break
        time.sleep(0.2)

    assert terminal is not None
    assert terminal["status"] == "completed"
