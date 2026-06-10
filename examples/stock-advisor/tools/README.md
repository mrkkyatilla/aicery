# StockPilot custom tools

Runtime hazır olunca her biri `ToolExecutorPort` üzerinden kayıt edilir.

| Tool | Input | Output |
|------|-------|--------|
| `get_stock` | `{ "sku": "string" }` | `{ "qty", "reorder_level", "warehouse" }` |
| `get_sales_velocity` | `{ "sku", "days": 30 }` | `{ "units_sold", "trend" }` |
| `search_suppliers` | `{ "sku" }` | `{ "offers": [{ "vendor", "price", "lead_days" }] }` |
| `suggest_promo` | `{ "sku", "context": "string" }` | `{ "headline", "rationale" }` |

Demo implementasyon: `data/*.csv|json` okuyan in-process Python (gerçek ERP yok).

**Aicery sağlar:** timeout, permission, trace satırı.  
**Siz sağlarsınız:** iş mantığı ve veri doğruluğu.
