# Contributing

Thank you for contributing to Aicery.

## Development setup

```bash
make install
make up          # Docker: postgres, redis, api, ...
make migrate
make unit
make lint
```

## Pull requests

1. Keep changes focused; match existing code style (`ruff`).
2. If you change the HTTP API, update [`runtime/openapi/openapi.v1.json`](runtime/openapi/openapi.v1.json) and [`guide/`](guide/) as needed.
3. Run relevant gates before opening a PR:

```bash
make unit
make lint
make gate-s4-modules          # opt-in modules regression
make gate-stock-product       # if PLUGIN_PATHS / examples changed
```

## Gates

Gate scripts live in [`scripts/`](scripts/). Module gates are documented in [`guide/modules/`](guide/modules/).

Internal sprint notes and phase plans are maintained in the private **aicery-internal** repository (team access only).

## Repository layout and SDK publish boundaries

This monorepo is the public source of truth on GitHub. Only a subset is published to package registries.

| Surface | Location | Published as |
|---------|----------|--------------|
| Runtime motor | `core/`, `runtime/`, `agents/`, `tools/`, `cli/` | GitHub only |
| Examples & guides | `examples/`, `guide/`, `adr/` | GitHub only |
| Python SDK | `sdk/python/` | PyPI: `aicery-sdk` (wheel built in CI; no `dist/` in repo) |
| TypeScript SDK | `sdk/typescript/` | npm: `@aicery/sdk` (source in repo; `dist/` built at publish time) |

**Never commit:** `.env`, `.aicery/`, `node_modules/`, build artifacts (`dist/`, `build/`, `*.egg-info/`).

The TypeScript lockfile (`sdk/typescript/package-lock.json`) is tracked for reproducible `npm ci` in CI and publish pipelines.

## Code of conduct

Be respectful and constructive in reviews and issues.
