import asyncio

import pytest

from tools.registry import REGISTRY, tool
from tools.registry.executor import RegistryToolExecutor, ToolPermissionDenied, ToolTimeout


@pytest.fixture(autouse=True)
def _clear_registry():
    REGISTRY.clear()
    yield
    REGISTRY.clear()


def test_allowlist_blocks_disallowed_tool() -> None:
    @tool("allowed_only", {"type": "object"})
    def allowed_only() -> dict:
        return {"ok": True}

    executor = RegistryToolExecutor(allowed_tools=["allowed_only"])

    async def _run():
        with pytest.raises(ToolPermissionDenied):
            await executor.invoke(
                "other",
                {},
                run_id="r1",
                agent_id="research",
            )

    asyncio.run(_run())


def test_timeout_tool(tmp_path) -> None:
    root = tmp_path

    @tool("slow", {"type": "object"})
    def slow(*, workspace_root: str = ".") -> dict:
        import time

        time.sleep(2)
        return {"done": True}

    executor = RegistryToolExecutor(workspace_root=str(root), timeout=0.5)

    async def _run():
        with pytest.raises(ToolTimeout):
            await executor.invoke("slow", {}, run_id="r1", agent_id="a")

    asyncio.run(_run())
