# Showcase examples

Runnable templates that show how to build vertical apps on the Aicery runtime. Each example includes demo data, optional custom tools, and a `scripts/demo.sh` smoke script.

**Prerequisites:** From repo root: `make install && make up` (use `USE_MOCK_PROVIDER=true` for local dev without live LLM API keys).

## Examples

| Folder | Product name | Description |
|--------|--------------|-------------|
| [stock-advisor](stock-advisor/) | StockPilot | Custom tools + `inventory-advisor` agent |
| [workspace-analyst](workspace-analyst/) | AskMyCorp | Policy Q&A over indexed documents |
| [runbook-agent](runbook-agent/) | Runbook Copilot | Read-only incident suggestions |
| [compliance-scan](compliance-scan/) | PolicyScan | Checklist scan over policy files |
| [support-drafter](support-drafter/) | ReplyAssist | KB-backed support draft |
| [sales-research](sales-research/) | LeadBrief | Lead research summary |
| [research-docs](research-docs/) | — | Semantic search E2E demo |
| [hello-agent](hello-agent/) | — | Minimal pytest smoke |

## Run all demos

```bash
make gate-demo-examples
```

Or individually:

```bash
bash examples/workspace-analyst/scripts/demo.sh
bash examples/stock-advisor/scripts/demo.sh
bash examples/runbook-agent/scripts/demo.sh
bash examples/compliance-scan/scripts/demo.sh
bash examples/support-drafter/scripts/demo.sh
bash examples/sales-research/scripts/demo.sh
```

## Architecture pattern

```txt
examples/<app>/
├── README.md
├── aicery.yaml
├── agents/          # manifests (optional)
├── tools/           # custom tools (PLUGIN_PATHS)
├── data/            # demo fixtures
└── scripts/demo.sh
```

**Motor provides:** runs, trace, replay, tool execution, LLM routing.  
**You provide:** UI, ERP connectors, business rules.

More scenarios: [https://aicery.dev/docs](https://aicery.dev/docs)
