from __future__ import annotations

from contextlib import contextmanager
from datetime import UTC

from opentelemetry import trace
from opentelemetry.trace import Span, StatusCode

from core.domain.run import Run
from core.domain.trace import TraceStep, TraceStepType
from runtime.observability.otel_setup import get_tracer, is_otel_active
from runtime.observability.request_context import get_org_id


class RunOtelContext:
    """Per-run span registry for trace step parent linkage."""

    def __init__(self, run: Run) -> None:
        self.run = run
        self.root_span: Span | None = None
        self._step_spans: dict[str, Span] = {}

    def register_step_span(self, step_id: str, span: Span) -> None:
        self._step_spans[step_id] = span

    def parent_span(self, parent_step_id: str | None) -> Span | None:
        if parent_step_id and parent_step_id in self._step_spans:
            return self._step_spans[parent_step_id]
        return self.root_span

    def export_step(self, step: TraceStep) -> None:
        if self.root_span is None:
            return
        parent = self.parent_span(step.parent_step_id)
        tracer = get_tracer()
        attrs = {**_base_attributes(step), **_type_attributes(step)}
        parent_context = trace.set_span_in_context(parent) if parent is not None else None
        start_ns = int(step.started_at.astimezone(UTC).timestamp() * 1e9)
        end_ns = (
            int(step.ended_at.astimezone(UTC).timestamp() * 1e9)
            if step.ended_at is not None
            else None
        )
        span = tracer.start_span(
            _span_name(step),
            context=parent_context,
            start_time=start_ns,
            attributes=attrs,
        )
        duration = _step_duration_ms(step)
        if duration is not None:
            span.set_attribute("aicery.duration_ms", duration)
        if step.status == "error":
            span.set_status(StatusCode.ERROR, step.error_code or "error")
        span.end(end_time=end_ns)
        self.register_step_span(step.step_id, span)

    def clear(self) -> None:
        self._step_spans.clear()
        self.root_span = None


def _base_attributes(step: TraceStep) -> dict[str, str | int | float | bool]:
    attrs: dict[str, str | int | float | bool] = {
        "aicery.run_id": step.run_id,
        "aicery.step_id": step.step_id,
        "aicery.step.type": step.type.value if isinstance(step.type, TraceStepType) else str(step.type),
        "aicery.status": step.status,
    }
    org_id = get_org_id()
    if org_id:
        attrs["aicery.org_id"] = org_id
    if step.input_hash:
        attrs["aicery.input_hash"] = step.input_hash
    if step.output_hash:
        attrs["aicery.output_hash"] = step.output_hash
    if step.error_code:
        attrs["aicery.error_code"] = step.error_code
    return attrs


def _span_name(step: TraceStep) -> str:
    if step.type == TraceStepType.AGENT:
        return "aicery.agent.step"
    if step.type == TraceStepType.LLM:
        return "aicery.llm"
    if step.type == TraceStepType.TOOL:
        return "aicery.tool"
    if step.type == TraceStepType.HUMAN:
        return "aicery.human.action"
    return "aicery.system.step"


def _type_attributes(step: TraceStep) -> dict[str, str | int | float | bool]:
    attrs: dict[str, str | int | float | bool] = {}
    meta = step.metadata or {}
    if step.type == TraceStepType.AGENT:
        if "node" in meta:
            attrs["aicery.node"] = str(meta["node"])
        if "step_index" in meta:
            attrs["aicery.step_index"] = int(meta["step_index"])
    elif step.type == TraceStepType.LLM:
        usage = meta.get("usage") or {}
        model = usage.get("model") or meta.get("model")
        if model:
            attrs["aicery.model"] = str(model)
        tokens_in = usage.get("tokens_in", 0)
        tokens_out = usage.get("tokens_out", 0)
        if tokens_in:
            attrs["gen_ai.usage.input_tokens"] = int(tokens_in)
        if tokens_out:
            attrs["gen_ai.usage.output_tokens"] = int(tokens_out)
    elif step.type == TraceStepType.TOOL:
        attrs["aicery.tool.name"] = step.name
        duration_ms = meta.get("duration_ms")
        if duration_ms is not None:
            attrs["aicery.duration_ms"] = int(duration_ms)
    elif step.type == TraceStepType.HUMAN:
        attrs["aicery.human_action"] = True
        if meta.get("decision"):
            attrs["aicery.decision"] = str(meta["decision"])
        if meta.get("tool_name"):
            attrs["aicery.tool.name"] = str(meta["tool_name"])
    elif step.type == TraceStepType.SYSTEM:
        if meta.get("graph_interrupt"):
            attrs["aicery.graph.interrupt"] = True
        if meta.get("interrupt_node"):
            attrs["aicery.graph.node"] = str(meta["interrupt_node"])
    return attrs


def _step_duration_ms(step: TraceStep) -> int | None:
    if step.ended_at is None:
        return None
    delta = step.ended_at - step.started_at
    return int(delta.total_seconds() * 1000)


@contextmanager
def run_otel_context(run: Run):
    if not is_otel_active():
        yield None
        return

    ctx = RunOtelContext(run)
    tracer = get_tracer()
    attrs = {
        "aicery.run_id": run.id,
        "aicery.agent_id": run.agent_id,
    }
    if run.conversation_id:
        attrs["aicery.conversation_id"] = run.conversation_id
    org_id = get_org_id()
    if org_id:
        attrs["aicery.org_id"] = org_id

    with tracer.start_as_current_span("aicery.run", attributes=attrs) as span:
        ctx.root_span = span
        try:
            yield ctx
        finally:
            span.set_attribute("aicery.status", run.status.value)
            if run.error_code:
                span.set_status(StatusCode.ERROR, run.error_code)
            ctx.clear()
