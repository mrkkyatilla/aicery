# aicery-sdk

Official **Python client** for the [Aicery](https://github.com/mrkkyatilla/aicery) AI agent runtime.

## About Aicery

**Aicery** is an open-source AI agent runtime — orchestration, tools, trace, and replay. It is the engine under your application, not a vertical SaaS product.

```
Agents are replaceable. Runtime is permanent.
```

The runtime runs LangGraph agents, executes tools safely, records step-by-step traces, and replays runs with frozen mocks. You bring UI, business rules, and data connectors; Aicery handles runs, providers, and observability.

- **Repository:** https://github.com/mrkkyatilla/aicery
- **Documentation:** https://aicery.dev/docs
- **License:** MIT

This package (`aicery-sdk`) is a thin HTTP client for the runtime API (`/v1/runs`, `/v1/agents`, SSE streaming). It does not include the runtime server — run the [Aicery stack](https://github.com/mrkkyatilla/aicery#quick-start) locally or point the client at your deployment.

## Install

```bash
pip install aicery-sdk
```

Requires Python 3.11+.

## Prerequisites

A running Aicery runtime (default: `http://localhost:8000`). From the main repo:

```bash
git clone https://github.com/mrkkyatilla/aicery.git
cd aicery
make install && make up && make migrate
```

Default API key for local dev: `dev`.

## Quick start

```python
from aicery_sdk import AiceryClient

client = AiceryClient(base_url="http://localhost:8000", api_key="dev")

run = client.create_run(agent_id="echo", input="hello", execute=True)
final = client.get_run(run.id)

print(final.status)       # completed
print(final.output_text)  # echo:hello
```

`create_run` may return `status: pending` immediately; call `get_run` for the final output.

## Configuration

**From `aicery.yaml`** (recommended in projects):

```python
client = AiceryClient.from_config("aicery.yaml")
```

**From environment:**

```python
client = AiceryClient.from_env()
# API_KEY or AICERY_API_KEY (default: dev)
# AICERY_RUNTIME_URL (default: http://localhost:8000)
```

## List agents

```python
agents = client.list_agents()
for agent in agents:
    print(agent["id"], agent.get("name"))
```

## Streaming

```python
run = client.create_run(agent_id="research", input="Summarize README", execute=True)

for event in client.stream_run(run.id):
    if event.event == "token":
        print(event.data, end="", flush=True)
```

## API surface (v0.0.x)

| Method | Description |
|--------|-------------|
| `create_run(...)` | Start or execute an agent run |
| `get_run(run_id)` | Fetch run status and output |
| `list_agents()` | List available agents |
| `stream_run(run_id)` | SSE token/step stream |
| `resume_run(...)` | HITL resume after approval |
| `from_config(path)` | Load client from `aicery.yaml` |
| `from_env()` | Load client from environment |

## Related

- [Getting started guide](https://github.com/mrkkyatilla/aicery/blob/main/guide/getting-started.md)
- [Python SDK guide](https://github.com/mrkkyatilla/aicery/blob/main/guide/python-sdk.md)
- [TypeScript SDK](https://www.npmjs.com/package/@aicery/sdk) (npm)

## Development

From the monorepo (editable install):

```bash
pip install -e ./sdk/python
pytest sdk/python/tests
```
