# ADR-005: Privacy Proxy (MOD-PRIVACY)

| | |
|--|--|
| Status | Accepted |
| Date | 2026-06-15 |

## Context

Enterprise deployments must reduce PII and secret leakage to external LLM providers. The core `ProviderPort` contract and `/v1/runs` API must remain unchanged; masking is an opt-in wrapper.

## Decisions

1. **Hook** — `PrivacyProxyProvider` wraps `ProviderPort`: pre-mask `messages` → inner LLM → post-unmask response text.
2. **Vault** — Run-scoped in-memory map `{placeholder → secret}` on the wrapper instance; cleared after each `complete` / `stream` call. No plaintext secrets in trace metadata.
3. **Entity v1 (regex)** — Email, Turkish national ID (11 digits), `0x` Ethereum wallet (40 hex), `sk-` / `api_key` style secrets.
4. **Fail policy** — `PRIVACY_PROXY_FAIL_CLOSED=true` (default): if residual PII patterns remain in outbound messages after masking, block the call with `PrivacyViolationError`.
5. **Tool path** — Same `mask_text` / `unmask_text` helpers may wrap tool-result summaries sent to the LLM (graph nodes); v1 gate focuses on provider wrap.
6. **Feature flag** — `PRIVACY_PROXY_ENABLED=false` by default; behavior identical to today when disabled.

## Consequences

- Golden PII set (`runtime/data/privacy/golden_pii.json`) + `make gate-privacy-proxy`.
- False negatives possible with regex-only v1; fail-closed mitigates outbound leaks at cost of blocked calls.
- Full NER v2 and locale-specific ID formats deferred.

## References

[`privacy_proxy.py`](../../runtime/runtime/adapters/providers/privacy_proxy.py) · [`factory.py`](../../runtime/runtime/adapters/providers/factory.py) · [`guide/modules/privacy-proxy.md`](../guide/modules/privacy-proxy.md)
