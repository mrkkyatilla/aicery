# ADR-006: Sandbox MVP (sidecar `sandbox-runner`)

| | |
|--|--|
| Status | Accepted |
| Date | 2026-06-15 |

## Context

`execute_code` tooling requires isolated code execution. Running `subprocess` inside the main API container is unacceptable for production threat models. This ADR records the MVP sidecar skeleton; full gVisor/Firecracker isolation is post-MVP.

## Decisions

1. **Sidecar** — `deploy/sandbox-runner`: minimal HTTP service `POST /execute {code, timeout_sec}` → Python `subprocess`, capture stdout/stderr with caps.
2. **Threat model (MVP)** — Network disabled in sidecar image policy (no outbound); request timeout (max 30s); stdout cap (64 KiB); non-root container user; no shell access from API.
3. **Runtime stub** — `tools/builtins/execute_code.py` HTTP client to sidecar; `EXECUTE_CODE_ENABLED=false` default; tool not auto-registered in builtin agents.
4. **Compose** — `sandbox-runner` service under Docker Compose profile `sandbox`.
5. **Production path** — Replace sidecar backend with gVisor/Firecracker runner; API contract unchanged.

## Consequences

- `make gate-sandbox` smoke: sidecar up → `execute_code("print(1)")` → stdout `1`.
- Main runtime must not invoke `subprocess` for user code (gate asserts stub uses HTTP only).
- Tool synthesis remains parked until hardened sandbox ships.

## References

[`deploy/sandbox-runner/runner.py`](../../deploy/sandbox-runner/runner.py) · [`execute_code.py`](../../tools/tools/builtins/execute_code.py)
