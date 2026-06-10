# How-to: Context compactor (MOD-COMPACT)

Compress long `conversation_id` hot-memory history into structured JSON to reduce token cost (CP-2). Default **off**.

## Enable

```bash
export HOT_MEMORY_ENABLED=true
export CONTEXT_COMPACTOR_ENABLED=true
export COMPACTOR_TURN_THRESHOLD=15      # default
export COMPACTOR_CHAR_THRESHOLD=8000    # default
```

Compaction runs before building LLM messages when both turn and character thresholds are exceeded.

## Output shape

v1 produces general JSON (no manifest `state_schema` yet):

```json
{
  "summary": "Compacted N conversation turns into structured memory.",
  "key_facts": ["snippet 1", "snippet 2"]
}
```

Hot memory turns are replaced with a single `[compacted]` assistant turn. A trace step `memory.compact` is recorded when a trace recorder is available.

## Gate

```bash
make gate-context-compactor
```

Fixture: 25 turns → system slot stays small; history collapses to compacted state.

## Related

- [Hot memory](agent.md)
- [https://aicery.dev/docs](https://aicery.dev/docs)
