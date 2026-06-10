# Configuration

Runtime settings via environment variables (see `runtime/runtime/config.py`).

## Core

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql+psycopg://...@localhost:5433/aicery` | Postgres |
| `API_KEY` | `dev` | Runtime API key (**change in production**) |
| `WORKSPACE_ROOT` | `.` | Tool filesystem jail root |
| `USE_MOCK_PROVIDER` | `false` | Use mock LLM (local dev) |

## Providers

| Variable | Description |
|----------|-------------|
| `OPENAI_API_KEY` | OpenAI provider |
| `GEMINI_API_KEY` | Gemini provider |
| `GROQ_API_KEY` | Groq provider |
| `ANTHROPIC_API_KEY` | Anthropic provider |
| `PROVIDER_FAILOVER_ENABLED` | `true` — fallback to mock on error |

## Search and memory

| Variable | Default | Description |
|----------|---------|-------------|
| `SEMANTIC_SEARCH_ENABLED` | `true` | Qdrant hybrid search |
| `QDRANT_URL` | `http://localhost:6333` | Vector store |
| `HOT_MEMORY_ENABLED` | `false` | Conversation turn cache |
| `PLUGIN_PATHS` | `""` | Comma-separated plugin dirs |

## Opt-in modules

| Variable | Default | Description |
|----------|---------|-------------|
| `PRIVACY_PROXY_ENABLED` | `false` | PII mask on LLM outbound |
| `CONTEXT_COMPACTOR_ENABLED` | `false` | Hot memory compaction |
| `ROUTER_LLM_ENABLED` | `false` | Tiered `/v1/route` LLM layer |
| `EXECUTE_CODE_ENABLED` | `false` | Sandbox `execute_code` tool |
| `SANDBOX_RUNNER_URL` | `http://localhost:8091` | Sidecar URL |

## Rate limiting

| Variable | Default |
|----------|---------|
| `RATE_LIMIT_ENABLED` | `true` |
| `RATE_LIMIT_PER_MINUTE` | `100` |
| `RATE_LIMIT_BACKEND` | `redis` |

Full reference: [https://aicery.dev/docs/reference/configuration](https://aicery.dev/docs/reference/configuration)
