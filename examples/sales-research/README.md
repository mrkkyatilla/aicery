# LeadBrief — Sales Research (Showcase)

## Sorun

SDR hesap başına 30+ dk public research.

## Motor vs ürün

| Aicery | Sizin ürün |
|--------|------------|
| `http_request` allowlist + chain | CRM `create_note`, etik kurallar |

## Agent (showcase)

Bu demo **custom agent kullanmaz** — motor `research` agent + `data/leads/acme-corp.md`.

İleride ürün tarafı: `agents/account-research.yaml` — pipeline: gather → summarize.

## Demo

```bash
make up
bash examples/sales-research/scripts/demo.sh
```

## PR

Public kaynak özeti — trace ile doğrulanabilir.

## Sınır

Scraping politikası ve KVKK sizin sorumluluğunuz; domain allowlist zorunlu.
