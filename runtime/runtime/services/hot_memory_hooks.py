from __future__ import annotations

from core.domain.run import Run
from runtime.adapters.memory.factory import get_hot_memory
from runtime.config import Settings
from runtime.services.trace_recorder import TraceRecorder


def memory_key_for_run(run: Run) -> str:
    return run.conversation_id or run.id


async def persist_run_turns(run: Run) -> None:
    memory = get_hot_memory()
    if memory is None or not run.output_text:
        return
    key = memory_key_for_run(run)
    await memory.append_turn(key, "user", run.input_text)
    await memory.append_turn(key, "assistant", run.output_text)


async def build_messages_with_history_async(
    memory_key: str,
    *,
    system: str,
    user_content: str,
    run_id: str | None = None,
    trace_recorder: TraceRecorder | None = None,
) -> list[dict]:
    await maybe_compact_history(
        memory_key,
        run_id=run_id,
        trace_recorder=trace_recorder,
    )
    messages: list[dict] = [{"role": "system", "content": system}]
    memory = get_hot_memory()
    if memory is not None:
        settings = Settings()
        turns = await memory.get_recent_turns(memory_key, limit=settings.hot_memory_turn_limit)
        for turn in turns:
            role = turn.get("role", "user")
            if role in ("user", "assistant"):
                messages.append({"role": role, "content": turn.get("content", "")})
    messages.append({"role": "user", "content": user_content})
    return messages


def _heuristic_compact(turns: list[dict]) -> dict:
    key_facts: list[str] = []
    for turn in turns:
        content = str(turn.get("content", "")).strip()
        if len(content) < 12:
            continue
        snippet = content[:120].replace("\n", " ")
        if snippet not in key_facts:
            key_facts.append(snippet)
        if len(key_facts) >= 8:
            break
    return {
        "summary": f"Compacted {len(turns)} conversation turns into structured memory.",
        "key_facts": key_facts,
    }


async def maybe_compact_history(
    memory_key: str,
    *,
    run_id: str | None = None,
    trace_recorder: TraceRecorder | None = None,
) -> bool:
    settings = Settings()
    if not settings.context_compactor_enabled:
        return False
    memory = get_hot_memory()
    if memory is None:
        return False

    turns = await memory.get_recent_turns(memory_key, limit=settings.hot_memory_turn_limit)
    if len(turns) < settings.compactor_turn_threshold:
        return False
    total_chars = sum(len(str(t.get("content", ""))) for t in turns)
    if total_chars < settings.compactor_char_threshold:
        return False

    compacted = _heuristic_compact(turns)
    await memory.replace_turns_with_compacted(memory_key, compacted)
    if trace_recorder is not None and run_id:
        trace_recorder.record_compaction(
            run_id=run_id,
            turns_before=len(turns),
            chars_before=total_chars,
            compacted=compacted,
        )
    return True
