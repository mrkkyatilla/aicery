from tools.registry.decorator import tool

from _paths import find_sales_row, find_stock_row

SUGGEST_PROMO_SCHEMA = {
    "type": "object",
    "properties": {
        "sku": {"type": "string"},
        "context": {"type": "string"},
    },
    "required": ["sku"],
}


@tool("suggest_promo", SUGGEST_PROMO_SCHEMA)
def suggest_promo(sku: str, context: str = "", *, workspace_root: str = ".") -> dict:
    stock = find_stock_row(workspace_root, sku)
    sales = find_sales_row(workspace_root, sku)
    qty = int(stock["qty"]) if stock else 0
    reorder = int(stock["reorder_level"]) if stock else 0
    trend = sales.get("trend", "flat") if sales else "unknown"

    if qty < reorder:
        headline = f"Reorder push for {sku}"
        rationale = (
            f"Stock {qty} is below reorder level {reorder}. "
            f"Prioritize supplier restock before promotions."
        )
    elif trend == "down":
        headline = f"Clearance bundle for {sku}"
        rationale = f"Sales trend is down; consider a short discount campaign."
    else:
        headline = f"Steady seller highlight for {sku}"
        rationale = f"Stock and sales are healthy; feature in newsletter or upsell."

    if context.strip():
        rationale = f"{rationale} Context: {context.strip()[:120]}"

    return {"headline": headline, "rationale": rationale}
