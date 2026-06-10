"""First-token p95 latency gate (E6 scorecard)."""

from __future__ import annotations

import os
import time

import httpx
import pytest
from tests.load.load_utils import stream_first_token_ms

pytestmark = pytest.mark.load

P95_LIMIT_MS = float(os.environ.get("P95_LIMIT_MS", "3000"))
SAMPLE_SIZE = int(os.environ.get("P95_SAMPLE_SIZE", "20"))
BASE = os.environ.get("AICERY_API_URL", "http://localhost:8000")
HEADERS = {"X-API-Key": os.environ.get("AICERY_API_KEY", "dev")}


def _p95(values: list[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = max(0, int(len(ordered) * 0.95) - 1)
    return ordered[idx]


def test_first_token_p95_under_limit() -> None:
    latencies: list[float] = []
    with httpx.Client(base_url=BASE, headers=HEADERS, timeout=60.0) as client:
        for i in range(SAMPLE_SIZE):
            created = client.post(
                "/v1/runs",
                json={"agent_id": "echo", "input": f"p95-{i}", "execute": True},
            )
            created.raise_for_status()
            run_id = created.json()["id"]
            deadline = time.monotonic() + 30.0
            while time.monotonic() < deadline:
                body = client.get(f"/v1/runs/{run_id}").json()
                if body["status"] in ("running", "pending"):
                    break
                if body["status"] in ("completed", "failed", "cancelled"):
                    break
                time.sleep(0.05)
            latencies.append(stream_first_token_ms(client, run_id))

    p95 = _p95(latencies)
    assert p95 < P95_LIMIT_MS, f"p95={p95:.0f}ms limit={P95_LIMIT_MS}ms samples={latencies}"
