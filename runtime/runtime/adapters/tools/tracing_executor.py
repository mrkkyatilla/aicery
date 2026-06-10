from __future__ import annotations

import time

from core.ports.tool_executor import ToolExecutorPort
from runtime.services.trace_recorder import TraceRecorder
from tools.registry.executor import ToolNotFound, ToolPermissionDenied, ToolTimeout


class TracingToolExecutor:
    """Records tool trace steps around a delegate executor."""

    def __init__(self, inner: ToolExecutorPort, recorder: TraceRecorder) -> None:
        self._inner = inner
        self._recorder = recorder

    async def invoke(
        self,
        tool_name: str,
        arguments: dict,
        *,
        run_id: str,
        agent_id: str,
        workspace_root: str | None = None,
    ) -> dict:
        started = time.monotonic()
        try:
            outcome = await self._inner.invoke(
                tool_name,
                arguments,
                run_id=run_id,
                agent_id=agent_id,
                workspace_root=workspace_root,
            )
            duration_ms = outcome.get("duration_ms", int((time.monotonic() - started) * 1000))
            self._recorder.record_tool(
                run_id=run_id,
                tool_name=tool_name,
                arguments=arguments,
                result=outcome.get("result"),
                duration_ms=duration_ms,
                success=True,
            )
            return outcome
        except (ToolPermissionDenied, ToolTimeout, ToolNotFound) as exc:
            duration_ms = int((time.monotonic() - started) * 1000)
            self._recorder.record_tool(
                run_id=run_id,
                tool_name=tool_name,
                arguments=arguments,
                result=None,
                duration_ms=duration_ms,
                success=False,
                error_code=exc.error_code,
            )
            raise
