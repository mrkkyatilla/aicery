from __future__ import annotations

import csv
import json
from pathlib import Path

from tools.sandbox.jail import jail_path

SHOWCASE_DATA = "examples/stock-advisor/data"


def data_dir(workspace_root: str) -> Path:
    return jail_path(workspace_root, SHOWCASE_DATA)


def read_stock_rows(workspace_root: str) -> list[dict[str, str]]:
    path = data_dir(workspace_root) / "stock.csv"
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def find_stock_row(workspace_root: str, sku: str) -> dict[str, str] | None:
    target = sku.strip().upper()
    for row in read_stock_rows(workspace_root):
        if row.get("sku", "").strip().upper() == target:
            return row
    return None


def read_sales_rows(workspace_root: str) -> list[dict[str, str]]:
    path = data_dir(workspace_root) / "sales.csv"
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def find_sales_row(workspace_root: str, sku: str) -> dict[str, str] | None:
    target = sku.strip().upper()
    for row in read_sales_rows(workspace_root):
        if row.get("sku", "").strip().upper() == target:
            return row
    return None


def load_suppliers(workspace_root: str) -> dict:
    path = data_dir(workspace_root) / "suppliers.json"
    return json.loads(path.read_text(encoding="utf-8"))
