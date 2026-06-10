# ADR-004: Tiered ROUTER-LLM (`/v1/route`)

| | |
|--|--|
| Status | Accepted |
| Date | 2026-06-08 |

## Context

The rule-based router ([`agent_router.py`](../../runtime/runtime/services/agent_router.py)) handles short greetings and keyword-heavy utterances well. Ambiguous or semantic inputs (e.g. policy questions without search keywords) need a lightweight LLM classification layer without changing the public `/v1/route` contract.

## Decisions

1. **Tiered routing** — (1) rule router first; if `confidence >= 0.85`, short-circuit (2) else LLM JSON classify (3) on parse failure, timeout, or low LLM confidence → rule result as fallback.
2. **LLM output** — Structured JSON: `{ "agent_id", "confidence", "reason" }`. Markdown fences stripped before parse.
3. **Allow-list** — After parse, `agent_id` must be in `allowed_agents` (or full registry when unset); otherwise fallback to rule result.
4. **Feature flag** — `ROUTER_LLM_ENABLED=false` by default; existing clients and tests unchanged when disabled.
5. **Mock router mode** — Mock provider recognizes system prompt marker `aicery-router-v1` and returns golden-intent JSON for gate tests without live API cost.
6. **Reason prefixes** — `rule:`, `llm:`, or `fallback:` prefix on `reason` when tiered router is enabled (traceability).

## Consequences

- `POST /v1/route` request/response schema unchanged; OpenAPI snapshot stable.
- Golden intent set (`runtime/data/router/golden_intents.json`) + `make gate-router-llm` for regression.
- Live Groq/Gemini router provider optional; gate uses mock only.
- Out of scope (v1): trace `type=router` metering, TS SDK `route()`, cost optimizer, embedding classifier.

## References

[`agent_router.py`](../../runtime/runtime/services/agent_router.py) · [`route.py`](../../runtime/runtime/api/routes/route.py) · [`guide/routing.md`](../guide/routing.md)
