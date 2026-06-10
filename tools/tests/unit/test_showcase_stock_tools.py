import asyncio
from pathlib import Path

import pytest

from agents.plugin_paths import parse_plugin_paths, set_plugin_roots
from tools.registry import REGISTRY
from tools.registry.executor import RegistryToolExecutor
from tools.registry.plugin_loader import load_plugin_paths, reset_loaded_modules

REPO_ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture
def stock_executor(monkeypatch):
    reset_loaded_modules()
    REGISTRY.clear()
    import tools.builtins.filesystem  # noqa: F401

    roots = parse_plugin_paths(
        "examples/stock-advisor",
        workspace_root=str(REPO_ROOT),
    )
    set_plugin_roots(roots)
    load_plugin_paths(roots)
    workspace_root = str(REPO_ROOT)
    executor = RegistryToolExecutor(
        workspace_root=workspace_root,
        allowed_tools=[
            "get_stock",
            "get_sales_velocity",
            "search_suppliers",
            "suggest_promo",
        ],
    )
    yield executor, workspace_root
    REGISTRY.clear()
    reset_loaded_modules()
    set_plugin_roots([])


def test_get_stock_sku_42(stock_executor) -> None:
    executor, workspace_root = stock_executor

    async def _run():
        outcome = await executor.invoke(
            "get_stock",
            {"sku": "SKU-42"},
            run_id="r1",
            agent_id="inventory-advisor",
            workspace_root=workspace_root,
        )
        assert outcome["result"]["qty"] == 12
        assert outcome["result"]["reorder_level"] == 50

    asyncio.run(_run())


def test_search_suppliers_alpha_supply(stock_executor) -> None:
    executor, workspace_root = stock_executor

    async def _run():
        outcome = await executor.invoke(
            "search_suppliers",
            {"sku": "SKU-42"},
            run_id="r1",
            agent_id="inventory-advisor",
            workspace_root=workspace_root,
        )
        vendors = {o["vendor"] for o in outcome["result"]["offers"]}
        assert "Alpha Supply" in vendors
        assert "Beta Wholesale" in vendors

    asyncio.run(_run())


def test_allowlist_blocks_builtin_when_not_allowed(stock_executor) -> None:
    executor, workspace_root = stock_executor

    async def _run():
        from tools.registry.executor import ToolPermissionDenied

        with pytest.raises(ToolPermissionDenied):
            await executor.invoke(
                "read_file",
                {"path": "README.md"},
                run_id="r1",
                agent_id="inventory-advisor",
                workspace_root=workspace_root,
            )

    asyncio.run(_run())
