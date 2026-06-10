# Getting started

Run the Aicery runtime locally and execute your first agent.

## Prerequisites

- Docker and Docker Compose
- Python 3.12+
- `make`

## Install

```bash
git clone https://github.com/aicery/aicery.git
cd aicery
make install
```

## Start the stack

```bash
make up
make migrate
```

Default API: `http://localhost:8000` with `API_KEY=dev`.

For local development without live LLM costs:

```bash
export USE_MOCK_PROVIDER=true
```

## First run (HTTP)

```bash
curl -s -X POST http://localhost:8000/v1/runs \
  -H "X-API-Key: dev" \
  -H "Content-Type: application/json" \
  -d '{"agent_id":"echo","input":"hello","execute":true}'
```

## First run (CLI)

```bash
aicery init .
aicery agent run echo -i "hello"
```

## Custom tools example

Load the StockPilot showcase plugins:

```bash
export PLUGIN_PATHS=examples/stock-advisor
export USE_MOCK_PROVIDER=true
export HITL_ENABLED=false
make up

bash examples/stock-advisor/scripts/demo.sh
```

## Next steps

- [Agents](agents.md)
- [Tools and plugins](plugins.md)
- [Examples](../examples/README.md)
- Full tutorials: [https://aicery.dev/docs](https://aicery.dev/docs)
