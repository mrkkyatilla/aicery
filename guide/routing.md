# Agent routing (`POST /v1/route`)

Tiered router: rule short-circuit → optional LLM JSON classify → rule fallback.

## Flow

1. **Rule router** — keyword/regex heuristics ([`agent_router.py`](../../runtime/runtime/services/agent_router.py)).
2. **Short-circuit** — when `confidence >= ROUTER_RULE_SHORT_CIRCUIT` (default `0.85`), return rule result (`reason` prefix `rule:`).
3. **LLM classify** — when `ROUTER_LLM_ENABLED=true`, call lightweight model; parse JSON `{ agent_id, confidence, reason }`; validate `agent_id` against allow-list (`reason` prefix `llm:`).
4. **Fallback** — on timeout, parse error, or low LLM confidence → rule result (`reason` prefix `fallback:`).

When `ROUTER_LLM_ENABLED=false` (default), only step 1 runs (backward compatible).

## Environment

| Variable | Default | Purpose |
|----------|---------|---------|
| `ROUTER_LLM_ENABLED` | `false` | Enable tiered LLM layer |
| `ROUTER_LLM_PROVIDER` | `mock` | `mock`, `groq`, or `gemini` |
| `ROUTER_LLM_MODEL` | `mock` | Model id for router provider |
| `ROUTER_LLM_CONFIDENCE_THRESHOLD` | `0.6` | Min LLM confidence to accept |
| `ROUTER_RULE_SHORT_CIRCUIT` | `0.85` | Skip LLM when rule confidence ≥ this |
| `ROUTER_LLM_TIMEOUT_SEC` | `5.0` | LLM timeout; then fallback |
| `USE_MOCK_PROVIDER` | `false` | Forces mock for router gate/tests |

## Example

```bash
export ROUTER_LLM_ENABLED=true USE_MOCK_PROVIDER=true

curl -s -X POST http://localhost:8000/v1/route \
  -H "X-API-Key: dev" \
  -H "Content-Type: application/json" \
  -d '{"input": "What does our refund policy say?"}' | jq
```

Response: `{ "agent_id": "research", "confidence": 0.82, "reason": "llm:mock golden match" }`.

## Golden intent set

Ten curated utterances in [`runtime/data/router/golden_intents.json`](../../runtime/data/router/golden_intents.json). Mock provider maps utterances to expected `agent_id` for gate tests.

See [CONTRIBUTING.md](../CONTRIBUTING.md) for regression gates.

## ADR

Design decisions: [ADR-004](../adr/004-router-llm.md).
