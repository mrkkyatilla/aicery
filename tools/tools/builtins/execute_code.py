from __future__ import annotations

import os

import httpx

from tools.registry import tool

EXECUTE_CODE_SCHEMA = {
    "type": "object",
    "properties": {
        "code": {"type": "string"},
        "timeout_sec": {"type": "integer", "minimum": 1, "maximum": 30},
    },
    "required": ["code"],
}


@tool("execute_code", EXECUTE_CODE_SCHEMA)
def execute_code(
    code: str,
    timeout_sec: int = 5,
    *,
    sandbox_runner_url: str | None = None,
) -> dict:
    """HTTP client to sandbox-runner sidecar (never subprocess in API process)."""
    if os.environ.get("EXECUTE_CODE_ENABLED", "false").lower() not in ("1", "true", "yes"):
        raise RuntimeError("execute_code is disabled (EXECUTE_CODE_ENABLED=false)")

    base = sandbox_runner_url or os.environ.get(
        "SANDBOX_RUNNER_URL",
        "http://localhost:8091",
    )
    url = f"{base.rstrip('/')}/execute"
    with httpx.Client(timeout=timeout_sec + 2) as client:
        resp = client.post(url, json={"code": code, "timeout_sec": timeout_sec})
        resp.raise_for_status()
        payload = resp.json()
    return {
        "stdout": payload.get("stdout", ""),
        "stderr": payload.get("stderr", ""),
        "exit_code": payload.get("exit_code", -1),
    }
