"""Optional chaos wrapper for tool invoke (E6 F2). Set CHAOS_TOOL_FAIL_RATE=0.0–1.0."""

from __future__ import annotations

import os
import random

from core.ports.tool_executor import ToolExecutorPort


class ToolChaosError(Exception):
    error_code = "TOOL_CHAOS_FAIL"


class ChaosToolExecutor:
    def __init__(self, inner: ToolExecutorPort, fail_rate: float | None = None) -> None:
        self._inner = inner
        if fail_rate is None:
            fail_rate = float(os.environ.get("CHAOS_TOOL_FAIL_RATE", "0"))
        self._fail_rate = max(0.0, min(1.0, fail_rate))

    async def invoke(
        self,
        tool_name: str,
        arguments: dict,
        *,
        run_id: str,
        agent_id: str,
        workspace_root: str | None = None,
    ) -> dict:
        if self._fail_rate > 0 and random.random() < self._fail_rate:
            raise ToolChaosError(f"Chaos injected failure for {tool_name}")
        return await self._inner.invoke(
            tool_name,
            arguments,
            run_id=run_id,
            agent_id=agent_id,
            workspace_root=workspace_root,
        )
