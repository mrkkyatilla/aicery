#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

export HOT_MEMORY_ENABLED=true
export HOT_MEMORY_BACKEND=memory
export CONTEXT_COMPACTOR_ENABLED=true
export COMPACTOR_TURN_THRESHOLD=5
export COMPACTOR_CHAR_THRESHOLD=200

echo "== MOD-COMPACT: unit tests =="
pytest runtime/tests/unit/test_context_compactor.py -q

echo "== MOD-COMPACT: 25-turn fixture compaction =="
python3 - <<'PY'
import asyncio
import os

os.environ["HOT_MEMORY_ENABLED"] = "true"
os.environ["HOT_MEMORY_BACKEND"] = "memory"
os.environ["CONTEXT_COMPACTOR_ENABLED"] = "true"
os.environ["COMPACTOR_TURN_THRESHOLD"] = "5"
os.environ["COMPACTOR_CHAR_THRESHOLD"] = "200"

from runtime.adapters.memory.in_memory_hot import InMemoryHotMemory
from runtime.services.hot_memory_hooks import build_messages_with_history_async, maybe_compact_history

async def main():
    memory = InMemoryHotMemory()
    import runtime.services.hot_memory_hooks as hooks
    import runtime.adapters.memory.factory as factory

    factory._memory_instance = memory
    hooks.get_hot_memory = lambda: memory  # type: ignore[assignment]

    key = "gate-conv"
    for i in range(25):
        await memory.append_turn(key, "user", f"turn-{i} " + ("payload " * 30))
        await memory.append_turn(key, "assistant", f"reply-{i} " + ("text " * 30))

    await maybe_compact_history(key)
    messages = await build_messages_with_history_async(key, system="S" * 50, user_content="go")
    system_slot = messages[0]["content"]
    assert len(system_slot) < 500, len(system_slot)
    history = [m for m in messages if m["role"] != "system"]
    assert len(history) <= 2
    print(f"system_chars={len(system_slot)} history_turns={len(history)}")

asyncio.run(main())
PY

echo "== MOD-COMPACT gate OK =="
