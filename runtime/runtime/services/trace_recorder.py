from __future__ import annotations

from datetime import UTC, datetime

from core.domain.trace import TraceStep, TraceStepType
from core.domain.usage import LlmUsage
from core.ports.trace import TracePort
from core.trace.hashing import hash_messages, hash_text, hash_tool_input, preview_text
from runtime.observability.run_context import RunOtelContext


class TraceRecorder:
    """Append-only trace writer used by orchestrator and tools (F3)."""

    def __init__(self, port: TracePort) -> None:
        self._port = port
        self._run_context: RunOtelContext | None = None

    def set_run_context(self, ctx: RunOtelContext | None) -> None:
        self._run_context = ctx

    def append(self, step: TraceStep) -> None:
        self._port.append(step)
        if self._run_context is not None:
            self._run_context.export_step(step)

    def record_agent_step(
        self,
        *,
        run_id: str,
        name: str,
        node: str,
        step_index: int,
        parent_step_id: str | None = None,
    ) -> TraceStep:
        step = TraceStep(
            run_id=run_id,
            type=TraceStepType.AGENT,
            name=name,
            parent_step_id=parent_step_id,
            input_hash=hash_text(f"{node}:{step_index}"),
            input_preview=preview_text(node),
            metadata={"node": node, "step_index": step_index},
            ended_at=datetime.now(UTC),
        )
        self.append(step)
        return step

    def record_llm(
        self,
        *,
        run_id: str,
        name: str,
        messages: list[dict],
        output: str,
        model: str = "",
        usage: LlmUsage | None = None,
        parent_step_id: str | None = None,
        status: str = "ok",
        error_code: str | None = None,
    ) -> TraceStep:
        ended = datetime.now(UTC)
        metadata: dict = {}
        if usage is not None:
            metadata["usage"] = usage.model_dump()
        step = TraceStep(
            run_id=run_id,
            type=TraceStepType.LLM,
            name=name,
            parent_step_id=parent_step_id,
            input_hash=hash_messages(messages, model=model),
            output_hash=hash_text(output) if output else None,
            input_preview=preview_text(str(messages)),
            output_preview=preview_text(output),
            metadata=metadata,
            status=status,  # type: ignore[arg-type]
            error_code=error_code,
            ended_at=ended,
        )
        self.append(step)
        return step

    def record_tool(
        self,
        *,
        run_id: str,
        tool_name: str,
        arguments: dict,
        result: dict | None,
        duration_ms: int,
        success: bool,
        error_code: str | None = None,
        parent_step_id: str | None = None,
    ) -> TraceStep:
        import json

        output_preview = json.dumps(result, default=str) if result is not None else None
        step = TraceStep(
            run_id=run_id,
            type=TraceStepType.TOOL,
            name=tool_name,
            parent_step_id=parent_step_id,
            input_hash=hash_tool_input(tool_name, arguments),
            output_hash=hash_text(output_preview or ""),
            input_preview=preview_text(json.dumps(arguments, sort_keys=True, default=str)),
            output_preview=preview_text(output_preview or ""),
            metadata={"duration_ms": duration_ms},
            status="ok" if success else "error",
            error_code=error_code,
            ended_at=datetime.now(UTC),
        )
        self.append(step)
        return step

    def record_compaction(
        self,
        *,
        run_id: str,
        turns_before: int,
        chars_before: int,
        compacted: dict,
        parent_step_id: str | None = None,
    ) -> TraceStep:
        step = TraceStep(
            run_id=run_id,
            type=TraceStepType.AGENT,
            name="memory.compact",
            parent_step_id=parent_step_id,
            input_hash=hash_text(f"compact:{turns_before}:{chars_before}"),
            output_hash=hash_text(str(compacted)),
            input_preview=preview_text(f"turns={turns_before} chars={chars_before}"),
            output_preview=preview_text(str(compacted)),
            metadata={
                "turns_before": turns_before,
                "chars_before": chars_before,
                "compacted": compacted,
            },
            ended_at=datetime.now(UTC),
        )
        self.append(step)
        return step
