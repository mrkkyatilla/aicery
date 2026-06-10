import time
from pathlib import Path

import httpx
import pytest

pytestmark = pytest.mark.integration

BASE = "http://localhost:8000"
HEADERS = {"X-API-Key": "dev"}


def test_research_run_smoke() -> None:
    readme = Path("README.md")
    if not readme.is_file():
        pytest.skip("README.md not in workspace root")

    response = httpx.post(
        f"{BASE}/v1/runs",
        json={
            "agent_id": "research",
            "input": "Read README.md and summarize",
            "execute": True,
        },
        headers=HEADERS,
        timeout=30.0,
    )
    assert response.status_code == 201
    run_id = response.json()["id"]

    terminal = None
    for _ in range(100):
        get_resp = httpx.get(f"{BASE}/v1/runs/{run_id}", headers=HEADERS, timeout=10.0)
        terminal = get_resp.json()
        if terminal["status"] in ("completed", "failed"):
            break
        time.sleep(0.3)

    assert terminal is not None
    assert terminal["status"] == "completed", terminal
