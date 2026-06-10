"""T2-E5-01 — examples/research-docs/run.sh against running API."""

import os
import subprocess
from pathlib import Path

import httpx
import pytest

pytestmark = pytest.mark.integration

EXAMPLE_DIR = Path(__file__).resolve().parents[2] / "examples" / "research-docs"


@pytest.mark.integration
def test_research_docs_run_script() -> None:
    if not httpx.get("http://localhost:8000/health", timeout=2.0).is_success:
        pytest.skip("API not running")

    env = {**os.environ, "AICERY_API_URL": "http://localhost:8000", "AICERY_API_KEY": "dev"}
    result = subprocess.run(
        ["bash", str(EXAMPLE_DIR / "run.sh")],
        cwd=EXAMPLE_DIR,
        env=env,
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert result.returncode == 0, result.stderr + result.stdout
