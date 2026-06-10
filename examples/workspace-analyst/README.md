# AskMyCorp — Workspace Analyst (Showcase)

**Built with Aicery** — referans #2 · MVP yeteneklerine en uygun demo

## Sorun

Şirket bilgisi PDF, wiki, sözleşme klasörlerinde; “iade süresi ne?” sorusu için 20 dk arama.

## Motor vs ürün

| Aicery | Sizin ürün |
|--------|------------|
| Index + `search_workspace` + `read_file` | Hangi klasörler, erişim |
| Trace’de cite (dosya + satır) | Slack/Teams bot, SSO |
| BYOK | — |

**Motor yapmaz:** SharePoint native sync, hazır Notion app.

## Agent

`agents/ask-policy.yaml` — tek agent ReAct, tools: `search_workspace`, `read_file`.

## Demo

```bash
./scripts/demo.sh
# Input: "İade politikası kaç gün?"
# Beklenen: data/policies/refund.md cite
```

## Reklam

*“Kendi dosyalarınıza soru sorun — cevap trace’de kanıtlı.”*
