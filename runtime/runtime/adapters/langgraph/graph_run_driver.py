from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Any

from core.domain.run import Run
from langgraph.types import Command
from runtime.services.hitl_coordinator import HitlCoordinator


class GraphRunDriver:
    """Shared LangGraph astream loop with interrupt → HITL approval handling."""

    def __init__(self, coordinator: HitlCoordinator) -> None:
        self._coordinator = coordinator

    async def stream(
        self,
        run: Run,
        graph: Any,
        *,
        config: dict,
        graph_input: dict | Command,
        graph_name: str,
        on_node: Callable[[str, dict], Awaitable[None]] | None = None,
        on_complete: Callable[[dict], AsyncIterator[dict]] | None = None,
    ) -> AsyncIterator[dict]:
        async for chunk in graph.astream(graph_input, config, stream_mode="updates"):
            if "__interrupt__" in chunk:
                interrupt_tuple = chunk["__interrupt__"]
                interrupt_obj = interrupt_tuple[0]
                payload = interrupt_obj.value if hasattr(interrupt_obj, "value") else interrupt_obj
                checkpoint_id = await self._coordinator.capture_checkpoint_id(graph, config)
                pending = self._coordinator.create_graph_pending(
                    run_id=run.id,
                    tool_name=str(payload.get("tool_name", "")),
                    arguments=dict(payload.get("arguments") or {}),
                    graph=str(payload.get("graph", graph_name)),
                    interrupt_node=payload.get("node"),
                    checkpoint_id=checkpoint_id,
                )
                self._coordinator.record_graph_interrupt(run.id, payload, pending.approval_id)
                yield self._coordinator.build_approval_chunk(
                    pending, interrupt_node=payload.get("node")
                )
                return

            for node_name, update in chunk.items():
                step_index = update.get("step_index", 0) if isinstance(update, dict) else 0
                yield {"type": "step", "node": node_name, "index": step_index}
                if on_node is not None:
                    await on_node(node_name, update if isinstance(update, dict) else {})

        final_snapshot = await graph.aget_state(config)
        final_values = final_snapshot.values if final_snapshot else {}
        if on_complete is not None:
            async for event in on_complete(final_values):
                yield event
