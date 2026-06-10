# @aicery/sdk (TypeScript)

Thin TypeScript client for the Aicery runtime HTTP API. Types are generated from [`runtime/openapi/openapi.v1.json`](../../runtime/openapi/openapi.v1.json).

## Requirements

- Node.js >= 18 (native `fetch`)

## Install (monorepo dev)

```bash
cd sdk/typescript
npm install
npm run build
```

## Codegen

```bash
npm run codegen   # openapi-typescript → src/generated/openapi.ts
```

## Usage

```typescript
import { AiceryClient } from "@aicery/sdk";

const client = new AiceryClient({
  baseUrl: "http://localhost:8000",
  apiKey: "dev",
});

// Or: AiceryClient.fromEnv() with AICERY_RUNTIME_URL + API_KEY

const run = await client.createRun({
  input: "Summarize README",
  agentId: "research",
  execute: true,
});

for await (const event of client.streamRun(run.id)) {
  if (event.event === "token") {
    console.log(event.data);
  }
}

const final = await client.getRun(run.id);
console.log(final.status, final.output_text);
```

## Tests

```bash
npm test                  # Vitest unit (mock fetch)
npm run test:integration  # live API smoke (requires make up)
```

## Gate

From repo root:

```bash
make gate-v3-sdk
```

## MVP scope (v0.0.1)

- `createRun`, `getRun`, `streamRun`, `fromEnv`
- Out of scope: `resumeRun`, `route`, workspace index, npm publish

Python parity reference: [`sdk/python/aicery_sdk/client.py`](../python/aicery_sdk/client.py).
