from __future__ import annotations

import json

from core.domain.errors import ReplayMismatchError
from core.domain.trace import TraceStep, TraceStepType
from core.trace.hashing import hash_tool_input


class MockToolExecutor:
    """Replay tool calls from trace steps (F3 / E4)."""

    def __init__(
        self,
        trace_steps: list[TraceStep],
        *,
        trace_recorder=None,
    ) -> None:
        self._recorder = trace_recorder
        self._by_hash: dict[str, TraceStep] = {}
        for step in trace_steps:
            if step.type == TraceStepType.TOOL and step.input_hash:
                self._by_hash[step.input_hash] = step

    async def invoke(
        self,
        tool_name: str,
        arguments: dict,
        *,
        run_id: str,
        agent_id: str,
        workspace_root: str | None = None,
    ) -> dict:
        key = hash_tool_input(tool_name, arguments)
        step = self._by_hash.get(key)
        if step is None or not step.output_preview:
            raise ReplayMismatchError(f"No tool trace for {tool_name} hash={key}")
        try:
            result = json.loads(step.output_preview)
        except json.JSONDecodeError as exc:
            raise ReplayMismatchError(f"Invalid tool trace output for {tool_name}") from exc
        duration_ms = int(step.metadata.get("duration_ms", 0))
        outcome = {"result": result, "duration_ms": duration_ms}
        if self._recorder is not None:
            self._recorder.record_tool(
                run_id=run_id,
                tool_name=tool_name,
                arguments=arguments,
                result=result,
                duration_ms=duration_ms,
                success=True,
            )
        return outcome
