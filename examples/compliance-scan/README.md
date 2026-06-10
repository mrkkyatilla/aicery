# PolicyScan — Compliance Doc Scan (Showcase)

## Sorun

KYC / tedarik sözleşmelerinde checklist maddeleri manuel taranıyor.

## Motor vs ürün

| Aicery | Sizin ürün |
|--------|------------|
| Batch agent runs, trace export | Checklist YAML, PDF rapor |
| Immutable audit (yol haritası) | Hukuk review UI |

**Sınır:** Hukuki tavsiye değil; bulgu listesi.

## Agent (showcase)

Bu demo **custom agent kullanmaz** — motor `research` agent + `data/policies/kyc-checklist.md`.

İleride ürün tarafı: `agents/compliance-scan.yaml` — tools: `read_file`, `check_clause` (keyword match).

## Demo

```bash
make up
bash examples/compliance-scan/scripts/demo.sh
```

## PR

Denetlenebilir AI tarama — fintech pilot.
