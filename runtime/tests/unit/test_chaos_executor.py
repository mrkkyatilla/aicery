import pytest

from runtime.adapters.tools.chaos_executor import ChaosToolExecutor, ToolChaosError
from tools.registry.executor import RegistryToolExecutor


@pytest.mark.asyncio
async def test_chaos_injects_failures(monkeypatch, tmp_path) -> None:
    (tmp_path / "README.md").write_text("hello", encoding="utf-8")
    inner = RegistryToolExecutor(workspace_root=str(tmp_path), allowed_tools=["read_file"])
    chaos = ChaosToolExecutor(inner, fail_rate=1.0)

    with pytest.raises(ToolChaosError):
        await chaos.invoke(
            "read_file",
            {"path": "README.md"},
            run_id="550e8400-e29b-41d4-a716-446655440000",
            agent_id="research",
        )


@pytest.mark.asyncio
async def test_chaos_zero_rate_passes_through(tmp_path) -> None:
    (tmp_path / "README.md").write_text("hello", encoding="utf-8")
    inner = RegistryToolExecutor(workspace_root=str(tmp_path), allowed_tools=["read_file"])
    chaos = ChaosToolExecutor(inner, fail_rate=0.0)

    outcome = await chaos.invoke(
        "read_file",
        {"path": "README.md"},
        run_id="550e8400-e29b-41d4-a716-446655440001",
        agent_id="research",
    )
    assert outcome["result"]["content"] == "hello"
