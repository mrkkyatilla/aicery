import pytest

from runtime.config import Settings
from runtime.services.agent_router import route_input, route_input_async
from runtime.services.llm_router import parse_router_response


def test_parse_router_response_valid_json():
    result = parse_router_response(
        '{"agent_id":"echo","confidence":0.9,"reason":"greeting"}',
        ["echo", "research"],
    )
    assert result is not None
    assert result.agent_id == "echo"
    assert result.confidence == 0.9
    assert result.reason == "greeting"


def test_parse_router_response_markdown_fence():
    raw = '```json\n{"agent_id":"research","confidence":0.75,"reason":"docs"}\n```'
    result = parse_router_response(raw, ["echo", "research"])
    assert result is not None
    assert result.agent_id == "research"


def test_parse_router_response_invalid_agent():
    result = parse_router_response(
        '{"agent_id":"unknown","confidence":0.9,"reason":"x"}',
        ["echo", "research"],
    )
    assert result is None


def test_parse_router_response_malformed():
    assert parse_router_response("not json", ["echo"]) is None
    assert parse_router_response('{"agent_id":"echo"}', ["echo"]) is None
    assert parse_router_response('{"agent_id":"echo","confidence":2,"reason":"x"}', ["echo"]) is None


@pytest.mark.asyncio
async def test_route_input_async_disabled_matches_rule(monkeypatch):
    monkeypatch.setenv("ROUTER_LLM_ENABLED", "false")
    rule = route_input("hello")
    result = await route_input_async("hello", settings=Settings())
    assert result.agent_id == rule.agent_id
    assert result.confidence == rule.confidence
    assert result.reason == rule.reason


@pytest.mark.asyncio
async def test_route_input_async_rule_short_circuit(monkeypatch):
    monkeypatch.setenv("ROUTER_LLM_ENABLED", "true")
    monkeypatch.setenv("USE_MOCK_PROVIDER", "true")
    result = await route_input_async("hello", settings=Settings())
    assert result.agent_id == "echo"
    assert result.reason.startswith("rule:")


@pytest.mark.asyncio
async def test_route_input_async_llm_semantic(monkeypatch):
    monkeypatch.setenv("ROUTER_LLM_ENABLED", "true")
    monkeypatch.setenv("USE_MOCK_PROVIDER", "true")
    result = await route_input_async(
        "What does our refund policy say?",
        settings=Settings(),
    )
    assert result.agent_id == "research"
    assert result.reason.startswith("llm:")
