# StockPilot — Stok & Tedarik Advisor (Showcase)

**Built with Aicery** (planlanan Aicery Labs referans uygulaması #1)

> Motor: orchestration, trace, replay · **Siz:** ERP verisi ve iş kuralları

## Çözdüğü sorun

Tedarikçi / distribütör:

- Stok ERP’de, tedarik fiyatları dağınık (Excel, mail, web)  
- Azalan ürün geç fark ediliyor  
- “Nereden ucuza alırız?” ve “hangi SKU’ya kampanya?” manuel  

## Aicery motoru ne yapar?

| Primitive | Kullanım |
|-----------|----------|
| Agent chain | `planner` → `supplier-scout` → `sales-advisor` |
| Tools | Sandbox + allowlist + `tool_calls` kaydı |
| Trace / replay | Yanlış tedarik önerisini debug |
| BYOK | LLM maliyeti işletmede |
| Workspace | Opsiyonel: fiyat listesi PDF index |

## Sizin (ürün) katmanınız

| Tool | Açıklama | Demo veri |
|------|----------|-----------|
| `get_stock` | SKU → miktar, reorder_level | `data/stock.csv` |
| `get_sales_velocity` | Son 30 gün satış | `data/sales.csv` |
| `search_suppliers` | SKU için tedarikçi/fiyat | `data/suppliers.json` |
| `suggest_promo` | Kampanya metni önerisi | LLM + satış verisi |

**Motor sağlamaz:** Logo/SAP connector, mobil push, otomatik satın alma emri.

## Agent manifest (taslak)

`agents/inventory-advisor.yaml` — bkz. dosya.

Pipeline: `research-chain` benzeri 3 node LangGraph graph.

## Demo senaryosu

**Girdi:** `SKU-42 için stok, tedarik ve satış önerisi`

**Beklenen trace adımları:**

1. `tool` get_stock  
2. `tool` get_sales_velocity  
3. `llm` planner  
4. `tool` search_suppliers  
5. `llm` sales-advisor  

**Çıktı:** Markdown özet: stok durumu + 2 tedarik seçeneği + 1 kampanya cümlesi.

```bash
# Repo kökünden: make up (HITL_ENABLED=false önerilir)
bash examples/stock-advisor/scripts/demo.sh
```

**Durum (STOCK-PRODUCT ✅):** `inventory-advisor` agent + 4 custom tools (`tools/*.py`) via `PLUGIN_PATHS`.  
Demo: `bash examples/stock-advisor/scripts/demo.sh` · Gate: `make gate-stock-product`.

```bash
export PLUGIN_PATHS=examples/stock-advisor
export USE_MOCK_PROVIDER=true HITL_ENABLED=false
make up
bash examples/stock-advisor/scripts/demo.sh
```

## Reklam cümlesi

*“ERP’nize bağlanan agent’lar. Orchestration Aicery’de — stok mantığı sizde.”*

## PR / marka

| Alan | Değer |
|------|--------|
| Showcase kod | `stock-advisor` |
| Halk adı | StockPilot |
| İleride domain | `stockpilot.ai` (opsiyonel) |
| Footer | Powered by Aicery |

## Sınırlar (dürüst)

- Hukuki / mali bağlayıcı tavsiye değil  
- Fiyat verisi demo; production’da API doğruluğu sizin sorumluluğunuz  
- Otonom PO yok — öneri only  

## Related

- [Examples catalog](../README.md)
- [Plugins guide](../../guide/plugins.md)
- [https://aicery.dev/docs](https://aicery.dev/docs)
