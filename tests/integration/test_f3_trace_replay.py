"""F3: trace API + replay headers against live API."""

import time

import httpx
import pytest

pytestmark = pytest.mark.integration

BASE = "http://localhost:8000"
HEADERS = {"X-API-Key": "dev"}


def _wait_completed(client: httpx.Client, run_id: str, *, attempts: int = 60) -> dict:
    body: dict = {}
    for _ in range(attempts):
        body = client.get(f"/v1/runs/{run_id}").json()
        if body.get("status") in ("completed", "failed", "cancelled"):
            return body
        time.sleep(0.25)
    return body


def _llm_signatures(steps: list[dict]) -> list[tuple]:
    return [
        (s["type"], s["name"], s["input_hash"], s.get("output_hash"))
        for s in steps
        if s["type"] == "llm"
    ]


def test_trace_after_echo_run() -> None:
    with httpx.Client(base_url=BASE, headers=HEADERS, timeout=60.0) as client:
        if client.get("/health").status_code != 200:
            pytest.skip("API not running")

        created = client.post(
            "/v1/runs",
            json={"agent_id": "echo", "input": "f3-trace", "execute": True},
        )
        assert created.status_code == 201
        run_id = created.json()["id"]

        _wait_completed(client, run_id)

        trace = client.get(f"/v1/runs/{run_id}/trace")
        assert trace.status_code == 200
        assert len(trace.json()["steps"]) >= 1


def test_replay_echo_no_live_provider() -> None:
    """Replay uses trace-backed provider: LLM step hashes match source, run completes.

    Works with USE_MOCK_PROVIDER=true (echo:...) or false (Gemini). Does not require
    mock output text — only deterministic replay from recorded trace.
    """
    with httpx.Client(base_url=BASE, headers=HEADERS, timeout=60.0) as client:
        if client.get("/health").status_code != 200:
            pytest.skip("API not running")

        created = client.post(
            "/v1/runs",
            json={"agent_id": "echo", "input": "f3-replay", "execute": True},
        )
        assert created.status_code == 201
        source_id = created.json()["id"]
        source_body = _wait_completed(client, source_id)
        if source_body.get("status") == "failed":
            code = source_body.get("error_code") or ""
            if code.startswith("PROVIDER"):
                pytest.skip(
                    f"Source run failed ({code}): start API with USE_MOCK_PROVIDER=true "
                    "for stable gate-f3, or retry when Gemini is available"
                )
        assert source_body["status"] == "completed", source_body

        source_trace = client.get(f"/v1/runs/{source_id}/trace").json()["steps"]
        source_llm = _llm_signatures(source_trace)
        assert source_llm, "source run must record at least one LLM trace step"

        replay = client.post(
            "/v1/runs",
            json={"agent_id": "echo", "input": "f3-replay", "execute": True},
            headers={
                **HEADERS,
                "X-Aicery-Replay-Mode": "replay",
                "X-Aicery-Source-Run-Id": source_id,
                "X-Aicery-Mock-Tools": "true",
            },
        )
        assert replay.status_code == 201
        replay_id = replay.json()["id"]
        replay_body = _wait_completed(client, replay_id)
        assert replay_body["status"] == "completed", replay_body

        replay_trace = client.get(f"/v1/runs/{replay_id}/trace").json()["steps"]
        replay_llm = _llm_signatures(replay_trace)
        assert replay_llm, "replay run must record LLM trace steps"

        assert source_llm[0] == replay_llm[0], (
            "replay LLM hashes must match source trace (TraceReplayProvider); "
            "if this fails, replay headers may not be applied or trace is empty"
        )

        replay_out = replay_body.get("output_text") or ""
        assert replay_out, "replay must produce output_text"

        # Optional: mock stack gives echo: prefix; live Gemini does not — do not require it.
        source_out = source_body.get("output_text") or ""
        if source_out.startswith("echo:"):
            assert replay_out.startswith("echo:"), "mock stack should replay echo: output"
