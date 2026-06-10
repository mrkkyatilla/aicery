# How-to: Privacy proxy (MOD-PRIVACY)

Opt-in PII masking for outbound LLM calls. Default **off** — enable only when integrating with external providers under KVKK/GDPR constraints.

## Enable

```bash
export PRIVACY_PROXY_ENABLED=true
export PRIVACY_PROXY_FAIL_CLOSED=true   # default; block if residual PII detected
```

Restart the runtime API after changing env vars.

## What it does

- Wraps `ProviderPort` after metering: masks email, Turkish national ID (11 digits), `0x` wallet addresses, and `sk-` / `api_key` patterns before the LLM call.
- Stores secrets in a run-scoped in-memory vault; unmasks the LLM response before returning to the agent.
- Trace previews never contain vault plaintext.

## Fail-closed

When `PRIVACY_PROXY_FAIL_CLOSED=true`, outbound messages are scanned after masking. If detectable PII remains, the call raises `PrivacyViolationError` instead of leaking data.

Set `PRIVACY_PROXY_FAIL_CLOSED=false` only in controlled dev environments.

## Golden regression

```bash
make gate-privacy-proxy
```

Uses `runtime/data/privacy/golden_pii.json` — asserts masked outbound text contains no plaintext secrets.

## Related

- [ADR-005: Privacy proxy](../../adr/005-privacy-proxy.md)
- [Replay](replay.md)
