"""Live research agent — requires GEMINI_API_KEY, README.md in workspace_root."""

from __future__ import annotations

import os
from datetime import UTC, datetime
from pathlib import Path

import pytest

from core.domain.run import Run, RunStatus
from runtime.adapters.langgraph_orchestrator import LangGraphOrchestrator
from runtime.adapters.providers.gemini import GeminiProvider
from runtime.config import Settings

pytestmark = pytest.mark.live

pytest.importorskip("google.genai")


def _require_key() -> str:
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not key:
        pytest.skip("GEMINI_API_KEY not set")
    return key


def _require_readme() -> Path:
    root = Path(Settings().workspace_root).resolve()
    readme = root / "README.md"
    if not readme.is_file():
        pytest.skip(f"README.md not found under workspace_root={root}")
    return readme


@pytest.mark.asyncio
async def test_research_live_reads_readme_and_summarizes(monkeypatch) -> None:
    _require_readme()
    monkeypatch.setenv("USE_MOCK_PROVIDER", "false")
    from agents.manifest import get_allowed_tools
    from tools.registry.executor import RegistryToolExecutor

    settings = Settings()

    def _executor(agent_id: str):
        return RegistryToolExecutor(
            workspace_root=settings.workspace_root,
            allowed_tools=get_allowed_tools(agent_id),
        )

    monkeypatch.setattr(
        "runtime.adapters.langgraph_orchestrator.build_tool_executor",
        _executor,
    )
    provider = GeminiProvider(api_key=_require_key())
    orchestrator = LangGraphOrchestrator(provider)
    now = datetime.now(UTC)
    run = Run(
        agent_id="research",
        input_text="Summarize README.md in two sentences.",
        status=RunStatus.PENDING,
        created_at=now,
        updated_at=now,
    )
    parts: list[str] = []
    tool_steps = 0
    async for chunk in orchestrator.stream(run):
        if chunk.get("type") == "token":
            parts.append(chunk.get("text", ""))
        elif chunk.get("type") == "error":
            pytest.fail(f"research stream error: {chunk}")
        elif chunk.get("type") == "step":
            tool_steps += 1
    output = "".join(parts).strip()
    assert output
    assert "echo:" not in output.lower()
    assert any(word in output.lower() for word in ("aicery", "agent", "runtime", "motor"))
