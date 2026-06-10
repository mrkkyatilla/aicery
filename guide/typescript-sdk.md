# How-to: TypeScript SDK

Node / browser automation client for the Aicery runtime API.

## Package

[`sdk/typescript`](../sdk/typescript) — npm name `@aicery/sdk` (monorepo local; publish later).

## Setup

```bash
cd sdk/typescript
npm install
npm run build
```

OpenAPI types regenerate on build:

```bash
npm run codegen
```

Contract source: [`runtime/openapi/openapi.v1.json`](../runtime/openapi/openapi.v1.json).

## Local dev against compose API

```bash
# repo root
make up   # USE_MOCK_PROVIDER=true
```

```typescript
import { AiceryClient } from "@aicery/sdk";

const client = AiceryClient.fromEnv();
const run = await client.createRun({
  input: "hello",
  agentId: "research",
  execute: false,
});
console.log(run.id, run.status);
```

Environment:

| Variable | Default |
|----------|---------|
| `AICERY_RUNTIME_URL` | `http://localhost:8000` |
| `API_KEY` / `AICERY_API_KEY` | `dev` |

## SSE streaming

`streamRun(runId)` yields `{ event, data }` objects — same event names as Python SDK (`token`, `status`, `done`, `approval_required`, …).

## Gate

```bash
make gate-v3-sdk
```

Runs unit tests + integration smoke (`createRun` + `getRun` against healthy API).

## Related

- Python SDK: [`sdk/python`](../python/)
- OpenAPI: [`runtime/openapi/openapi.v1.json`](../runtime/openapi/openapi.v1.json)
- Cursor context: [`cursor-integration.md`](cursor-integration.md)
