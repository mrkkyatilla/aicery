# Agents

Run built-in and plugin agents via CLI or HTTP API.

## Prerequisites

```bash
make up && make migrate
aicery init .
```

## Built-in agents

| Agent | Tools | Use case |
|-------|-------|----------|
| `echo` | none | Smoke test, replay |
| `research` | read/list/search/http | Workspace document Q&A |

List agents:

```bash
curl -s http://localhost:8000/v1/agents -H "X-API-Key: dev" | jq
```

Manifests: `agents/builtins/manifests/*.yaml`.

## CLI

```bash
aicery agent run echo -i "hello"
aicery workspace index guide/
aicery agent run research -i "Summarize getting started"
```

| Flag | Description |
|------|-------------|
| `-i` / `--input` | User message |
| `--stream` / `--no-stream` | SSE vs poll |
| `--config` | Path to `aicery.yaml` |

## HTTP API

```bash
curl -s -X POST http://localhost:8000/v1/runs \
  -H "X-API-Key: dev" -H "Content-Type: application/json" \
  -d '{"agent_id":"research","input":"Summarize README","execute":true}'
```

## Routing

```bash
curl -s -X POST http://localhost:8000/v1/route \
  -H "X-API-Key: dev" \
  -d '{"input":"Search docs for refund policy"}' | jq
```

See [routing.md](routing.md) for tiered LLM router.

## Manifest anatomy

```yaml
id: research
version: "1.0.0"
tools:
  - read_file
  - search_workspace
pipelines:
  - research-chain
graph: agents.graphs.research:build_research_graph
system_prompt: |
  You summarize workspace files...
```

## Plugin agents

Custom agents via `PLUGIN_PATHS` — see [plugins.md](plugins.md).

## Related

- [Tools](tools.md)
- [Replay](replay.md)
- [examples/](../examples/README.md)
