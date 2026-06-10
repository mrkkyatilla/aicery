from __future__ import annotations

import re
from typing import TypedDict

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, StateGraph

from agents.registry import register_plugin_agent
from core.domain.replay import ReplayContext
from core.domain.run import Run
from core.ports.provider import ProviderPort
from core.ports.tool_executor import ToolExecutorPort


class InventoryState(TypedDict):
    messages: list[dict]
    step_index: int


def _extract_sku(text: str) -> str:
    match = re.search(r"SKU-\d+", text, re.IGNORECASE)
    return match.group(0).upper() if match else "SKU-42"


def build_inventory_advisor_graph(
    provider: ProviderPort,
    tools: ToolExecutorPort | None = None,
    run: Run | None = None,
    *,
    checkpointer: BaseCheckpointSaver | None = None,
    replay_ctx: ReplayContext | None = None,
):
    del replay_ctx
    if tools is None or run is None:
        raise ValueError("inventory-advisor requires tools and run")

    async def analyze(state: InventoryState) -> dict:
        user = state["messages"][-1]["content"]
        sku = _extract_sku(user)

        stock = await tools.invoke(
            "get_stock",
            {"sku": sku},
            run_id=run.id,
            agent_id=run.agent_id,
        )
        velocity = await tools.invoke(
            "get_sales_velocity",
            {"sku": sku, "days": 30},
            run_id=run.id,
            agent_id=run.agent_id,
        )
        suppliers = await tools.invoke(
            "search_suppliers",
            {"sku": sku},
            run_id=run.id,
            agent_id=run.agent_id,
        )
        promo = await tools.invoke(
            "suggest_promo",
            {"sku": sku, "context": user[:200]},
            run_id=run.id,
            agent_id=run.agent_id,
        )

        stock_r = stock["result"]
        vel_r = velocity["result"]
        sup_r = suppliers["result"]
        promo_r = promo["result"]
        offers = sup_r.get("offers") or []
        vendor_names = ", ".join(o["vendor"] for o in offers[:3]) or "none"

        summary_data = (
            f"SKU: {sku}\n"
            f"Stock qty: {stock_r['qty']}, reorder: {stock_r['reorder_level']}, "
            f"warehouse: {stock_r['warehouse']}\n"
            f"Sales (30d): {vel_r['units_sold']}, trend: {vel_r['trend']}\n"
            f"Suppliers: {vendor_names}\n"
            f"Promo: {promo_r['headline']} — {promo_r['rationale']}\n"
        )
        messages = [
            {
                "role": "system",
                "content": "Sen bir tedarik ve stok danışmanısın. Veriyi kısa Türkçe özetle.",
            },
            {"role": "user", "content": summary_data},
        ]
        text = await provider.complete(messages)
        return {
            "messages": [*state["messages"], {"role": "assistant", "content": text}],
            "step_index": state.get("step_index", 0) + 4,
        }

    graph = StateGraph(InventoryState)
    graph.add_node("analyze", analyze)
    graph.set_entry_point("analyze")
    graph.add_edge("analyze", END)
    return graph.compile(checkpointer=checkpointer)


register_plugin_agent("inventory-advisor", build_inventory_advisor_graph)
