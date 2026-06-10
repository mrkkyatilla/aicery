# ADR-003: Marketplace Browse MVP (curated registry)

| | |
|--|--|
| Status | Accepted |
| Date | 2026-06-08 |

## Context

GTM and integrators need a discoverable list of showcase plugins and builtin agents before a full marketplace (DB, publish, install, signatures). A read-only HTTP API is the first platform slice.

## Decisions

1. **Endpoint** — Runtime exposes `GET /v1/marketplace/plugins` (browse only). Future `GET /v1/marketplace/items` may alias; v1 path is `plugins`.
2. **Registry source** — Static curated JSON at `runtime/data/marketplace/plugins.json`, updated via PR (no user upload).
3. **Trust model** — Each card has `trust_level`: `verified` (Aicery-curated) or `community` (future). MVP entries are `verified` only.
4. **Auth** — Same as other runtime routes: `require_auth` (`X-API-Key` or JWT when enabled).
5. **Out of scope (v1)** — Install, publish, tarball, signature verify, Postgres `marketplace_items`, Stripe, browse UI.

## Consequences

- Registry changes are code review, not runtime mutation.
- Agent code still lives in customer workspace or signed bundles (motor boundary unchanged).
- Future DB-backed registry can preserve the same JSON response shape.

## References

[`runtime/data/marketplace/plugins.json`](../../runtime/data/marketplace/plugins.json) · [`examples/`](../examples/) · [https://aicery.dev/docs/concepts/motor-vs-your-app](https://aicery.dev/docs/concepts/motor-vs-your-app)
