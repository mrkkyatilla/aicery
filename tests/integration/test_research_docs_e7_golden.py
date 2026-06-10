"""E7-β1 — examples/research-docs: index + research cites MVP_SCOPE.md."""

from __future__ import annotations

import os
import time

import httpx
import pytest

pytestmark = [pytest.mark.integration, pytest.mark.e7_integration]

BASE = os.environ.get("AICERY_API_URL", "http://localhost:8000")
HEADERS = {"X-API-Key": os.environ.get("AICERY_API_KEY", "dev")}
INDEX_PATHS = ["examples/research-docs/docs/"]
QUERY = os.environ.get(
    "E7_GOLDEN_QUERY",
    "What is MVP scope? Use workspace search, then read "
    "examples/research-docs/docs/golden-scope.md and list must-have areas "
    "including semantic workspace search.",
)
WORKSPACE_ID = os.environ.get("DEFAULT_WORKSPACE_ID", "local")
# Phrases unique to examples/research-docs/docs/golden-scope.md (not root README).
CITE_PATTERNS = (
    "golden target",
    "semantic workspace search",
    "explicitly out of scope",
)


def _poll_run(client: httpx.Client, run_id: str, *, timeout_sec: float = 180.0) -> dict:
    deadline = time.monotonic() + timeout_sec
    while time.monotonic() < deadline:
        response = client.get(f"/v1/runs/{run_id}")
        response.raise_for_status()
        body = response.json()
        if body["status"] in ("completed", "failed", "cancelled"):
            return body
        time.sleep(0.5)
    raise TimeoutError(f"run {run_id} did not finish in {timeout_sec}s")


@pytest.mark.integration
@pytest.mark.e7_integration
def test_e7_research_docs_golden_index_and_cite(require_qdrant) -> None:
    with httpx.Client(base_url=BASE, headers=HEADERS, timeout=120.0) as client:
        if not client.get("/health").is_success:
            pytest.skip("API not running — make up")

        index_resp = client.post(
            "/v1/workspace/index",
            json={"workspace_id": WORKSPACE_ID, "paths": INDEX_PATHS},
        )
        if index_resp.status_code == 503:
            pytest.skip(f"semantic index unavailable: {index_resp.text}")
        index_resp.raise_for_status()
        indexed = index_resp.json()
        assert indexed["files_indexed"] >= 1, indexed
        assert indexed["chunks_upserted"] >= 1, indexed

        run_resp = client.post(
            "/v1/runs",
            json={"agent_id": "research", "input": QUERY, "execute": True},
        )
        run_resp.raise_for_status()
        run_id = run_resp.json()["id"]
        final = _poll_run(client, run_id)

    assert final["status"] == "completed", final
    text = (final.get("output_text") or "").lower()
    assert any(p in text for p in CITE_PATTERNS), (
        f"output did not cite MVP_SCOPE content: {final.get('output_text', '')[:500]}"
    )
