from __future__ import annotations

from collections.abc import AsyncIterator

from core.domain.errors import ReplayMismatchError
from core.domain.trace import TraceStep, TraceStepType
from core.domain.usage import LlmUsage
from core.trace.hashing import hash_messages


class TraceReplayProvider:
    """F3 replay provider: LLM outputs from recorded trace (no external API)."""

    def __init__(self, trace_steps: list[TraceStep], *, model: str = "") -> None:
        self._model = model
        self._by_input_hash: dict[str, TraceStep] = {}
        self._last_step: TraceStep | None = None
        self.last_usage: LlmUsage | None = None
        for step in trace_steps:
            if step.type == TraceStepType.LLM and step.input_hash:
                self._by_input_hash[step.input_hash] = step

    def _lookup(self, messages: list[dict]) -> TraceStep:
        key = hash_messages(messages, model=self._model)
        step = self._by_input_hash.get(key)
        if step is None or not step.output_preview:
            raise ReplayMismatchError(f"No trace match for input_hash={key}")
        self._last_step = step
        raw = (step.metadata or {}).get("usage")
        if isinstance(raw, dict):
            self.last_usage = LlmUsage.model_validate(raw)
        else:
            self.last_usage = None
        return step

    def pop_usage(self) -> LlmUsage | None:
        usage = self.last_usage
        self.last_usage = None
        return usage

    async def complete(self, messages: list[dict], **kwargs) -> str:
        return self._lookup(messages).output_preview or ""

    async def stream(self, messages: list[dict], **kwargs) -> AsyncIterator[str]:
        text = await self.complete(messages, **kwargs)
        if not text:
            return
        chunk_size = max(1, len(text) // 8)
        for i in range(0, len(text), chunk_size):
            yield text[i : i + chunk_size]
