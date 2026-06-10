import json
from collections import defaultdict


class InMemoryHotMemory:
    def __init__(self) -> None:
        self._turns: dict[str, list[dict]] = defaultdict(list)
        self._compacted: dict[str, dict] = {}

    async def append_turn(self, run_id: str, role: str, content: str) -> None:
        self._turns[run_id].append({"role": role, "content": content})

    async def get_recent_turns(self, run_id: str, limit: int = 20) -> list[dict]:
        return self._turns[run_id][-limit:]

    async def clear(self, run_id: str) -> None:
        self._turns.pop(run_id, None)
        self._compacted.pop(run_id, None)

    async def get_compacted_state(self, run_id: str) -> dict | None:
        return self._compacted.get(run_id)

    async def set_compacted_state(self, run_id: str, state: dict) -> None:
        self._compacted[run_id] = state

    async def replace_turns_with_compacted(self, run_id: str, state: dict) -> None:
        payload = json.dumps(state, ensure_ascii=False)
        self._turns[run_id] = [{"role": "assistant", "content": f"[compacted] {payload}"}]
        self._compacted[run_id] = state
