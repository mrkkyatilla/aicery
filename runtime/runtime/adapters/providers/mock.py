import asyncio
import json
import os
from collections.abc import AsyncIterator
from functools import lru_cache
from pathlib import Path

from core.domain.usage import LlmUsage
from runtime.adapters.providers.usage_helpers import estimate_usage

_ROUTER_SYSTEM_MARKER = "aicery-router-v1"


class MockProvider:
    """Deterministic provider for tests and local dev without API keys."""

    def __init__(self) -> None:
        self.last_usage: LlmUsage | None = None
        self._model = "mock"

    @staticmethod
    def _user_content(messages: list[dict]) -> str:
        user = next((m["content"] for m in reversed(messages) if m.get("role") == "user"), "")
        if isinstance(user, str) and user.startswith("__slow__:"):
            return user[len("__slow__:") :]
        return user

    @staticmethod
    def _is_router_prompt(messages: list[dict]) -> bool:
        system = next((m["content"] for m in messages if m.get("role") == "system"), "")
        return isinstance(system, str) and _ROUTER_SYSTEM_MARKER in system

    @staticmethod
    @lru_cache(maxsize=1)
    def _golden_intents() -> dict[str, str]:
        golden_file = (
            Path(__file__).resolve().parents[3] / "data" / "router" / "golden_intents.json"
        )
        if not golden_file.is_file():
            return {}
        with golden_file.open(encoding="utf-8") as f:
            cases = json.load(f)
        return {c["input"]: c["expected_agent_id"] for c in cases if "input" in c}

    def _router_response(self, messages: list[dict]) -> str:
        user = self._user_content(messages)
        utterance = user
        prefix = "Utterance to route:\n"
        if isinstance(user, str) and user.startswith(prefix):
            utterance = user[len(prefix) :]
        agent_id = self._golden_intents().get(utterance, "research")
        confidence = 0.82 if utterance in self._golden_intents() else 0.55
        reason = "mock golden match" if utterance in self._golden_intents() else "mock default"
        return json.dumps(
            {"agent_id": agent_id, "confidence": confidence, "reason": reason},
            separators=(",", ":"),
        )

    async def complete(self, messages: list[dict], **kwargs) -> str:
        if self._is_router_prompt(messages):
            text = self._router_response(messages)
        else:
            user = self._user_content(messages)
            text = f"echo:{user}"
        self.last_usage = estimate_usage(messages, text, provider="mock", model=self._model)
        return text

    async def stream(self, messages: list[dict], **kwargs) -> AsyncIterator[str]:
        raw_user = next((m["content"] for m in reversed(messages) if m.get("role") == "user"), "")
        if isinstance(raw_user, str) and raw_user.startswith("__slow__:"):
            await asyncio.sleep(float(os.environ.get("MOCK_STREAM_DELAY_SEC", "2.0")))
        text = await self.complete(messages, **kwargs)
        if not text:
            return
        target_chunks = int(os.environ.get("MOCK_STREAM_CHUNKS", "8"))
        chunk_size = max(1, len(text) // target_chunks)
        pieces = [text[i : i + chunk_size] for i in range(0, len(text), chunk_size)] or [text]
        for piece in pieces:
            yield piece
        emitted = len(pieces)
        idx = 0
        while emitted < target_chunks and text:
            yield text[idx % len(text)]
            idx += 1
            emitted += 1
