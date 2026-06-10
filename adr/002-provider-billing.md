# ADR-002: Provider Router & Cloud Metering (Post-MVP P4)

| | |
|--|--|
| Status | Accepted |
| Date | 2026-05-21 |

## Context

MVP uses a single provider. Post-MVP adds multi-LLM routing and cloud metering; billing UI ships later.

## Decisions

1. **BYOK default** — encrypted provider key per workspace.
2. **Capability router** — `deep_reasoning` / `fast`; model id in agent manifest.
3. **Usage events** — append-only metering; no invoice generation in first cloud slice.
4. **LLM credits** — feature flag; default off.

## Consequences

- Aicery runtime API is billed separately; LLM pass-through uses BYOK.
- Provider keys never appear in plaintext trace or log output.

## References

[`runtime/runtime/adapters/providers/`](../../runtime/runtime/adapters/providers/) · [https://aicery.dev/docs/enterprise/billing](https://aicery.dev/docs/enterprise/billing)
