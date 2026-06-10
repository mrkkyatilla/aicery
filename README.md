# Aicery

**AI agent runtime** — orchestration, tools, trace, and replay. Not a vertical SaaS product; the engine under your app.

```
Agents are replaceable. Runtime is permanent.
```

**Documentation:** [https://aicery.dev/docs](https://aicery.dev/docs)  
**Developer guides:** [guide/](guide/)

## What it is

Aicery runs LangGraph agents, executes tools safely, records step-by-step traces, and replays runs with frozen mocks. You bring UI, business rules, and data connectors; the runtime handles runs, providers, and observability.

## Quick start

```bash
make install
make up && make migrate
curl -s -X POST http://localhost:8000/v1/runs \
  -H "X-API-Key: dev" -H "Content-Type: application/json" \
  -d '{"agent_id":"echo","input":"hello","execute":true}'
```

See [guide/getting-started.md](guide/getting-started.md) for details.

## SDKs

**Python:**

```bash
pip install aicery-sdk
```

Monorepo dev: `pip install -e ./sdk/python`

```python
from aicery_sdk import AiceryClient
client = AiceryClient.from_config("aicery.yaml")
run = client.create_run(agent_id="echo", input="hello", execute=True)
```

**TypeScript** (monorepo):

```bash
cd sdk/typescript && npm install && npm run build
```

```typescript
import { AiceryClient } from "@aicery/sdk";
const client = AiceryClient.fromEnv();
const run = await client.createRun({ agentId: "echo", input: "hello", execute: true });
```

Published: [`pip install aicery-sdk`](https://pypi.org/project/aicery-sdk/) · `npm install @aicery/sdk` coming soon

## Examples

| Example | Description |
|---------|-------------|
| [stock-advisor](examples/stock-advisor/) | Custom tools + `inventory-advisor` agent |
| [workspace-analyst](examples/workspace-analyst/) | Document Q&A over indexed policies |
| [research-docs](examples/research-docs/) | Semantic search demo |

Full list: [examples/README.md](examples/README.md)

## Repository layout

| Path | Purpose |
|------|---------|
| `runtime/` | HTTP API, orchestrator, providers |
| `agents/` | Built-in agent graphs and manifests |
| `tools/` | Tool registry and builtins |
| `cli/` | `aicery` CLI |
| `sdk/` | Python and TypeScript clients |
| `guide/` | Technical developer guides |
| `adr/` | Architecture decision records |
| `examples/` | Runnable showcase applications |

## Enterprise

Multi-tenant gateway, billing, and advanced ops docs: [https://aicery.dev/docs](https://aicery.dev/docs)

## License

[MIT](LICENSE)
