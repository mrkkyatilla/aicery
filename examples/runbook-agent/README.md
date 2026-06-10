# Runbook Copilot — Incident Advisor (Showcase)

**Built with Aicery** — referans #3 · “Production-safe AI” PR

## Sorun

Gece yarısı latency alarmı; runbook var ama uygulama yavaş; panikte yanlış kubectl.

## Motor vs ürün

| Aicery | Sizin ürün |
|--------|------------|
| Read-only tool policy | `query_metrics` (mock → Datadog) |
| Trace + replay eğitim | Onay UI, PagerDuty hook |
| Audit trail (P7 plan) | — |

**Bilerek yok:** `kubectl_apply`, `restart_service` write tool’ları demo’da.

## Agent (showcase)

Bu demo **custom agent kullanmaz** — motor `research` agent + indexlenmiş runbook (`data/runbooks/`).

İleride ürün tarafı: `agents/incident-advisor.yaml` — tools: `read_runbook`, `query_metrics` (mock).

## Demo

```bash
# Repo kökünden (HITL_ENABLED=false önerilir)
make up
bash examples/runbook-agent/scripts/demo.sh
```

Input: checkout API p95 > 2s alarmı → runbook’tan scale / cache / rollback önerileri.

## Reklam

*“Önerir, production’a dokunmaz — her adım kayıtlı.”*

## Sınır

Otomatik remediation yok; SRE onayı şart.
