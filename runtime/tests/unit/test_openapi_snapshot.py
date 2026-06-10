"""T2-E5-02 — OpenAPI paths frozen for SDK contract."""

import json
from pathlib import Path

import pytest

from runtime.api.app import create_app

SNAPSHOT = Path(__file__).resolve().parents[2] / "openapi" / "openapi.v1.json"

REQUIRED_PATHS = {
    "/health",
    "/v1/runs",
    "/v1/runs/{run_id}",
    "/v1/runs/{run_id}/stream",
    "/v1/runs/{run_id}/trace",
    "/v1/runs/{run_id}/usage",
    "/v1/runs/{run_id}/resume",
    "/v1/agents",
    "/v1/workspace/index",
    "/v1/workspace/index/jobs/{job_id}",
    "/v1/route",
    "/v1/marketplace/plugins",
}


def test_openapi_contains_required_paths() -> None:
    schema = create_app().openapi()
    paths = set(schema.get("paths", {}))
    missing = REQUIRED_PATHS - paths
    assert not missing, f"missing OpenAPI paths: {missing}"


def test_openapi_snapshot_matches() -> None:
    schema = create_app().openapi()
    if not SNAPSHOT.is_file():
        SNAPSHOT.parent.mkdir(parents=True, exist_ok=True)
        SNAPSHOT.write_text(json.dumps(schema, indent=2, sort_keys=True) + "\n")
        pytest.skip(f"Wrote new snapshot to {SNAPSHOT}")

    expected = json.loads(SNAPSHOT.read_text())
    assert set(schema.get("paths", {})) == set(expected.get("paths", {}))
