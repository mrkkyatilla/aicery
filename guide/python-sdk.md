# Python SDK

Thin client for the Aicery runtime HTTP API.

## Install (monorepo)

```bash
pip install -e ./sdk/python
```

Published package (`pip install aicery-sdk`) coming soon.

## Usage

```python
from aicery_sdk import AiceryClient

client = AiceryClient.from_config("aicery.yaml")

run = client.create_run(
    agent_id="echo",
    input="hello",
    execute=True,
)

final = client.get_run(run.id)
print(final.status, final.output_text)
```

## Streaming

```python
for event in client.stream_run(run.id):
    print(event)
```

## Environment

| Variable | Default |
|----------|---------|
| `API_KEY` | `dev` |
| Base URL | from `aicery.yaml` or `http://localhost:8000` |

## Related

- [Getting started](getting-started.md)
- [TypeScript SDK](typescript-sdk.md)
