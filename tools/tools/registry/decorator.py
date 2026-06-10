from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass
class ToolDefinition:
    name: str
    input_schema: dict
    handler: Callable[..., Any]


REGISTRY: dict[str, ToolDefinition] = {}


def tool(name: str, schema: dict):
    def deco(fn: Callable[..., Any]):
        REGISTRY[name] = ToolDefinition(name=name, input_schema=schema, handler=fn)
        return fn

    return deco
