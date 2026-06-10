# ADR-001: MVP Technology Stack

| | |
|--|--|
| Status | Accepted |
| Date | 2026-05-21 |

## Context

Aicery needs a single-node, developer-first runtime before scale-out. Competing options (Temporal vs LangGraph-only core, K8s vs Compose, UI-first vs CLI-first) are resolved here for MVP.

## Decisions

1. **Runtime language** — Python 3.11+ with FastAPI + Uvicorn.
2. **Architecture** — Modular monolith; `/core` ports are framework-free; adapters live in `/runtime`.
3. **Orchestration** — LangGraph only (no Temporal in MVP).
4. **Deploy** — Docker Compose on one node (Postgres 16, Redis 7, NATS 2, API). Qdrant for semantic search.
5. **Data** — PostgreSQL (structured runs), Redis (hot memory), NATS (events).
6. **Surface** — CLI-first; no web UI in MVP.
7. **Auth** — API key header stub; JWT later.
8. **Provider** — Single provider (Gemini) behind `ProviderPort`; router multi-provider post-MVP ([ADR-002](./002-provider-billing.md)).
9. **Out of scope** — K8s, billing, marketplace, visual builder, GPU cluster.

## Consequences

- All teams depend on E1 port contracts; breaking changes require schema version bumps.
- E2 route handlers stay thin; LangGraph never imported from `/core`.
- Go/Rust kernel migration remains possible via stable ports.

## References

[`runtime/`](../../runtime/) · [`deploy/docker-compose.yml`](../../deploy/docker-compose.yml)
