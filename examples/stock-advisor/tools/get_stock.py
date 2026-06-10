from tools.registry.decorator import tool

from _paths import find_stock_row

GET_STOCK_SCHEMA = {
    "type": "object",
    "properties": {"sku": {"type": "string"}},
    "required": ["sku"],
}


@tool("get_stock", GET_STOCK_SCHEMA)
def get_stock(sku: str, *, workspace_root: str = ".") -> dict:
    row = find_stock_row(workspace_root, sku)
    if row is None:
        raise ValueError(f"SKU not found: {sku}")
    return {
        "qty": int(row["qty"]),
        "reorder_level": int(row["reorder_level"]),
        "warehouse": row["warehouse"],
    }
