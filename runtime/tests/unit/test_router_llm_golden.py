import pytest

from runtime.config import Settings
from runtime.services.agent_router import route_input_async
from runtime.services.llm_router import load_golden_intents


@pytest.mark.parametrize("case", load_golden_intents())
@pytest.mark.asyncio
async def test_golden_intent(case, monkeypatch):
    monkeypatch.setenv("ROUTER_LLM_ENABLED", "true")
    monkeypatch.setenv("USE_MOCK_PROVIDER", "true")
    result = await route_input_async(
        case["input"],
        allowed_agents=case.get("allowed_agents"),
        settings=Settings(),
    )
    assert result.agent_id == case["expected_agent_id"]
