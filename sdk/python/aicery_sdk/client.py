from __future__ import annotations

import json
import os
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx
import yaml

_DEFAULT_RUNTIME_URL = "http://localhost:8000"


@dataclass
class Run:
    id: str
    status: str
    agent_id: str
    input_text: str | None = None
    output_text: str | None = None
    error_code: str | None = None
    error_message: str | None = None


@dataclass
class SseEvent:
    event: str
    data: dict[str, Any]


class AiceryClient:
    def __init__(self, base_url: str, api_key: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key

    @classmethod
    def from_config(cls, config_path: str | Path = "aicery.yaml") -> "AiceryClient":
        path = cls._resolve_config_path(config_path)
        if path is None:
            if cls._dev_fallback_allowed():
                return cls.from_env()
            raise FileNotFoundError(
                f"Config not found: {config_path}\n"
                "Create one with: aicery init .\n"
                "Or set API_KEY=dev (and optional AICERY_RUNTIME_URL) for local dev."
            )
        data = yaml.safe_load(path.read_text())
        if not isinstance(data, dict):
            raise ValueError(f"Invalid aicery.yaml: {path}")
        config_dir = path.parent
        key_file = config_dir / str(data.get("api_key_file", ".aicery/api_key"))
        if key_file.is_file():
            api_key = key_file.read_text().strip()
        else:
            api_key = os.environ.get("API_KEY") or os.environ.get("AICERY_API_KEY", "dev")
        return cls(
            base_url=str(data.get("runtime_url", _DEFAULT_RUNTIME_URL)),
            api_key=api_key,
        )

    @classmethod
    def _resolve_config_path(cls, config_path: str | Path) -> Path | None:
        env_path = os.environ.get("AICERY_CONFIG")
        if env_path:
            candidate = Path(env_path)
            if candidate.is_file():
                return candidate

        path = Path(config_path)
        if path.is_file():
            return path

        for parent in [Path.cwd(), *Path.cwd().parents[:3]]:
            candidate = parent / "aicery.yaml"
            if candidate.is_file():
                return candidate
        return None

    @classmethod
    def _dev_fallback_allowed(cls) -> bool:
        if os.environ.get("API_KEY") or os.environ.get("AICERY_API_KEY"):
            return True
        if Path(".aicery/api_key").is_file():
            return True
        return os.environ.get("AICERY_DEV", "1") != "0"

    @classmethod
    def from_env(cls) -> "AiceryClient":
        api_key = os.environ.get("API_KEY") or os.environ.get("AICERY_API_KEY", "dev")
        base_url = os.environ.get("AICERY_RUNTIME_URL", _DEFAULT_RUNTIME_URL)
        key_file = Path(".aicery/api_key")
        if key_file.is_file():
            api_key = key_file.read_text().strip()
        return cls(base_url=base_url, api_key=api_key)

    def _headers(self) -> dict[str, str]:
        return {"X-API-Key": self._api_key}

    def create_run(
        self,
        *,
        agent_id: str | None = None,
        input: str,
        pipeline: str | None = None,
        workspace_id: str | None = None,
        conversation_id: str | None = None,
        execute: bool = True,
        provider_policy: dict[str, Any] | None = None,
        replay_source_run_id: str | None = None,
        mock_tools: bool = False,
    ) -> Run:
        payload: dict[str, Any] = {"input": input, "execute": execute}
        if agent_id:
            payload["agent_id"] = agent_id
        if pipeline:
            payload["pipeline"] = pipeline
        if workspace_id:
            payload["workspace_id"] = workspace_id
        if conversation_id:
            payload["conversation_id"] = conversation_id
        if provider_policy:
            payload["provider_policy"] = provider_policy
        headers = self._headers()
        if replay_source_run_id:
            headers["X-Aicery-Replay-Mode"] = "replay"
            headers["X-Aicery-Source-Run-Id"] = replay_source_run_id
            if mock_tools:
                headers["X-Aicery-Mock-Tools"] = "true"
        with httpx.Client(base_url=self._base_url, timeout=60.0) as client:
            response = client.post("/v1/runs", json=payload, headers=headers)
            response.raise_for_status()
            body = response.json()
        return Run(
            id=body["id"],
            status=body["status"],
            agent_id=body["agent_id"],
            input_text=body.get("input_text"),
            output_text=body.get("output_text"),
            error_code=body.get("error_code"),
            error_message=body.get("error_message"),
        )

    def resume_run(
        self,
        run_id: str,
        *,
        decision: str,
        approval_id: str | None = None,
        arguments: dict[str, Any] | None = None,
    ) -> Run:
        payload: dict[str, Any] = {"decision": decision}
        if approval_id:
            payload["approval_id"] = approval_id
        if arguments is not None:
            payload["arguments"] = arguments
        with httpx.Client(base_url=self._base_url, timeout=30.0) as client:
            response = client.post(
                f"/v1/runs/{run_id}/resume",
                json=payload,
                headers=self._headers(),
            )
            response.raise_for_status()
            body = response.json()
        return Run(
            id=body["id"],
            status=body["status"],
            agent_id=body["agent_id"],
            input_text=body.get("input_text"),
            output_text=body.get("output_text"),
            error_code=body.get("error_code"),
            error_message=body.get("error_message"),
        )

    def wait_for_approval(
        self,
        run_id: str,
        *,
        poll_interval_sec: float = 0.2,
        timeout_sec: float = 300.0,
    ) -> Run:
        """Poll run status until it leaves ``suspended`` (or timeout)."""
        import time

        deadline = time.monotonic() + timeout_sec
        while time.monotonic() < deadline:
            run = self.get_run(run_id)
            if run.status != "suspended":
                return run
            time.sleep(poll_interval_sec)
        raise TimeoutError(f"Run {run_id} still suspended after {timeout_sec}s")

    def get_run(self, run_id: str) -> Run:
        with httpx.Client(base_url=self._base_url, timeout=30.0) as client:
            response = client.get(f"/v1/runs/{run_id}", headers=self._headers())
            response.raise_for_status()
            body = response.json()
        return Run(
            id=body["id"],
            status=body["status"],
            agent_id=body["agent_id"],
            input_text=body.get("input_text"),
            output_text=body.get("output_text"),
            error_code=body.get("error_code"),
            error_message=body.get("error_message"),
        )

    def route(self, input_text: str, *, allowed_agents: list[str] | None = None) -> dict[str, Any]:
        payload: dict[str, Any] = {"input": input_text}
        if allowed_agents:
            payload["allowed_agents"] = allowed_agents
        with httpx.Client(base_url=self._base_url, timeout=30.0) as client:
            response = client.post("/v1/route", json=payload, headers=self._headers())
            response.raise_for_status()
            return response.json()

    def index_workspace(
        self,
        *,
        workspace_id: str = "local",
        paths: list[str],
    ) -> dict[str, Any]:
        with httpx.Client(base_url=self._base_url, timeout=300.0) as client:
            response = client.post(
                "/v1/workspace/index",
                json={"workspace_id": workspace_id, "paths": paths},
                headers=self._headers(),
            )
            response.raise_for_status()
            return response.json()

    def get_trace(self, run_id: str) -> dict[str, Any]:
        with httpx.Client(base_url=self._base_url, timeout=30.0) as client:
            response = client.get(f"/v1/runs/{run_id}/trace", headers=self._headers())
            response.raise_for_status()
            return response.json()

    def get_run_usage(self, run_id: str) -> dict[str, Any]:
        with httpx.Client(base_url=self._base_url, timeout=30.0) as client:
            response = client.get(f"/v1/runs/{run_id}/usage", headers=self._headers())
            response.raise_for_status()
            return response.json()

    def save_last_run_id(self, run_id: str) -> None:
        path = Path(".aicery/last_run_id")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(run_id)

    def list_agents(self) -> list[dict]:
        with httpx.Client(base_url=self._base_url, timeout=30.0) as client:
            response = client.get("/v1/agents", headers=self._headers())
            response.raise_for_status()
            return response.json().get("agents", [])

    def stream_run(self, run_id: str) -> Iterator[SseEvent]:
        headers = {**self._headers(), "Accept": "text/event-stream"}
        with httpx.Client(base_url=self._base_url, timeout=None) as client:
            with client.stream("GET", f"/v1/runs/{run_id}/stream", headers=headers) as response:
                response.raise_for_status()
                event_name: str | None = None
                data_lines: list[str] = []
                for raw in response.iter_lines():
                    if raw is None:
                        continue
                    line = raw.strip()
                    if not line:
                        if event_name and data_lines:
                            yield SseEvent(
                                event=event_name,
                                data=json.loads("\n".join(data_lines)),
                            )
                        event_name = None
                        data_lines = []
                        continue
                    if line.startswith("event:"):
                        event_name = line[6:].strip()
                    elif line.startswith("data:"):
                        data_lines.append(line[5:].strip())
