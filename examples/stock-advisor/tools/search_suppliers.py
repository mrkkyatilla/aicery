from tools.registry.decorator import tool

from _paths import load_suppliers

SEARCH_SUPPLIERS_SCHEMA = {
    "type": "object",
    "properties": {"sku": {"type": "string"}},
    "required": ["sku"],
}


@tool("search_suppliers", SEARCH_SUPPLIERS_SCHEMA)
def search_suppliers(sku: str, *, workspace_root: str = ".") -> dict:
    data = load_suppliers(workspace_root)
    key = sku.strip().upper()
    raw = data.get(key) or data.get(sku) or []
    offers = [
        {
            "vendor": item["vendor"],
            "price": item["price"],
            "lead_days": item["lead_days"],
        }
        for item in raw
    ]
    return {"offers": offers}
