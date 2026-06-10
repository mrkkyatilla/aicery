# aicery.dev site content manifest

This file maps public website pages to source material. The website is a **separate repository**; implement with your chosen static site generator (e.g. Astro, Docusaurus, Mintlify).

## Site structure

| URL | Type | Source (rewrite, do not copy verbatim) |
|-----|------|----------------------------------------|
| `/` | Marketing | README positioning + hero trio from internal `planning/SHOWCASE_EXAMPLES.md` |
| `/docs/get-started/install` | Tutorial | `guide/getting-started.md` |
| `/docs/get-started/python-sdk` | Tutorial | `guide/python-sdk.md` |
| `/docs/get-started/typescript-sdk` | Tutorial | `guide/typescript-sdk.md` + `sdk/typescript/README.md` |
| `/docs/concepts/what-is-the-runtime` | Explanation | Internal `architecture/motor-boundaries.md` |
| `/docs/concepts/motor-vs-your-app` | Explanation | Internal `architecture/motor-boundaries.md` |
| `/docs/concepts/infrastructure-for-ai` | Explanation | Internal `architecture/infrastructure-for-ai.md` |
| `/docs/guides/custom-tools` | How-to | `guide/plugins.md` |
| `/docs/guides/stock-tracking-app` | How-to | `examples/stock-advisor/` + Tauri scenario (new) |
| `/docs/guides/cursor` | How-to | Internal `how-to/cursor-integration.md` rewrite |
| `/docs/guides/trace-debug` | How-to | `guide/replay.md` |
| `/docs/reference/api` | Reference | OpenAPI codegen from `runtime/openapi/openapi.v1.json` |
| `/docs/reference/cli` | Reference | `cli/` typer commands |
| `/docs/reference/configuration` | Reference | `guide/configuration.md` expanded |
| `/docs/enterprise/gateway` | Explanation | Internal `how-to/tenant-gateway.md` |
| `/docs/enterprise/billing` | Explanation | Internal `how-to/billing-ui.md` |
| `/examples` | Gallery | `examples/README.md` per-app pages |

## Sync policy

- **Per release tag:** copy `guide/` and OpenAPI snapshot into site repo.
- **Internal only:** sprint notes, phase plans, gate matrices — never publish.

## Out of scope for v1 site

- npm/PyPI publish automation (separate dilim)
- Interactive API playground (optional v1.1)
