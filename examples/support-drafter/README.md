# ReplyAssist — Support Draft (Showcase)

## Sorun

Destek ekibi aynı makroları kopyalıyor; KB güncel değil.

## Motor vs ürün

| Aicery | Sizin ürün |
|--------|------------|
| KB index + draft agent | Zendesk/Intercom API, gönder onayı |

## Agent (showcase)

Bu demo **custom agent kullanmaz** — motor `research` agent + ticket + KB (`data/tickets/`, `data/kb/`).

İleride ürün tarafı: `agents/draft-reply.yaml` — `search_workspace`, `get_ticket` (mock).

## Demo

```bash
make up
bash examples/support-drafter/scripts/demo.sh
```

## PR

Bağlamlı draft — makro değil.
