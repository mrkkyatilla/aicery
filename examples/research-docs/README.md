# research-docs — F2 + E7 golden demo

Summarize markdown via the `research` agent. E7 path indexes docs into Qdrant first.

## Quick (F2)

```bash
make up   # from repo root
./run.sh
```

## E7 golden (index → research → cite `docs/MVP_SCOPE.md`)

From **repo root** (API must mount repo at `/workspace`):

```bash
make up
./examples/research-docs/run_e7.sh
```

Or:

```bash
aicery workspace index examples/research-docs/docs/
aicery agent run research --config examples/research-docs/aicery.yaml \
  --input "What is MVP scope? List the must-have areas from the workspace documentation."
```

Requires API at `http://localhost:8000`, Qdrant healthy, `SEMANTIC_SEARCH_ENABLED=true`.
