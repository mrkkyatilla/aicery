# Trace and replay

Debug runs without calling live LLM or tool APIs again.

## Inspect trace

```bash
aicery trace last
aicery trace <run_id>
```

## Replay with frozen mocks

```bash
aicery replay last --mock-tools
```

Replay uses the source run trace for LLM outputs and (optionally) tool results. Input text must match the source run.

Headers: `X-Aicery-Replay-Mode: replay`, `X-Aicery-Source-Run-Id`, `X-Aicery-Mock-Tools: true`.

## Graph topology

```bash
aicery graph
aicery graph research-chain
aicery graph -f mermaid research-chain
```

## Drift check (opt-in module)

Soft regression report against golden fixtures:

```bash
aicery drift check
aicery drift check --baseline runtime/data/drift/golden_runs.json
```

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `No last run` | Run an agent first |
| `REPLAY_INPUT_MISMATCH` | Input must match source |
| `REPLAY_MISMATCH` | Trace missing step for current code path |

## Related

- [Agents](agents.md)
- [Tools](tools.md)
