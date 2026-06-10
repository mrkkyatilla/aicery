# Research golden scope doc

Golden target for semantic search demos in `examples/research-docs/`.

## What is MVP scope?

The MVP is a composable AI agent runtime (CLI-first, not a UI platform).

### Must-have areas

1. **Brain orchestrator** — planning, provider routing, retry/fallback, streaming
2. **Agent runtime** — YAML/Python agents, tool allowlists, echo + research + sequential chain
3. **Tool layer** — `read_file`, `list_files`, `search_workspace`, `http_request` with jail/SSRF guards
4. **Trace & replay** — step timeline, deterministic replay with frozen tool mocks
5. **Semantic workspace search** — index markdown into Qdrant; hybrid vector + grep fallback

### Explicitly out of scope (MVP)

- Visual builder, marketplace, billing, Kubernetes, GPU router, parallel multi-agent swarms

### North-star feeling

> Agent workflow crashed → trace → replay → fixed in minutes.
