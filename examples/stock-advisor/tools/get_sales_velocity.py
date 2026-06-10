from tools.registry.decorator import tool

from _paths import find_sales_row

GET_SALES_VELOCITY_SCHEMA = {
    "type": "object",
    "properties": {
        "sku": {"type": "string"},
        "days": {"type": "integer"},
    },
    "required": ["sku"],
}


@tool("get_sales_velocity", GET_SALES_VELOCITY_SCHEMA)
def get_sales_velocity(sku: str, days: int = 30, *, workspace_root: str = ".") -> dict:
    row = find_sales_row(workspace_root, sku)
    if row is None:
        return {"units_sold": 0, "trend": "unknown", "days": days}
    return {
        "units_sold": int(row["units_sold_30d"]),
        "trend": row.get("trend", "flat"),
        "days": days,
    }
