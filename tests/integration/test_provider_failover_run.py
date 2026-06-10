"""T3-E6-03: run completes when failover is active (mock primary path via compose)."""

import httpx
import pytest

pytestmark = pytest.mark.integration

BASE = "http://localhost:8000"
HEADERS = {"X-API-Key": "dev"}


def test_echo_run_completes_with_failover_enabled() -> None:
    """With USE_MOCK_PROVIDER=true, factory uses mock only; smoke that API still runs."""
    with httpx.Client(base_url=BASE, headers=HEADERS, timeout=60.0) as client:
        if client.get("/health").status_code != 200:
            pytest.skip("API not running")
        created = client.post(
            "/v1/runs",
            json={"agent_id": "echo", "input": "failover-smoke", "execute": True},
        )
        assert created.status_code == 201
        run_id = created.json()["id"]
        for _ in range(60):
            body = client.get(f"/v1/runs/{run_id}").json()
            if body["status"] in ("completed", "failed", "cancelled"):
                assert body["status"] == "completed"
                return
        pytest.fail("run did not complete")
