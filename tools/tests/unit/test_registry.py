from tools.registry import REGISTRY, tool


def test_tool_registers_handler() -> None:
    REGISTRY.clear()

    @tool("ping", {"type": "object"})
    def ping() -> dict:
        return {"pong": True}

    assert "ping" in REGISTRY
    assert REGISTRY["ping"].handler() == {"pong": True}
