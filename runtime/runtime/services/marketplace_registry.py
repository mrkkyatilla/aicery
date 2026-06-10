from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

_REGISTRY_FILE = (
    Path(__file__).resolve().parents[2] / "data" / "marketplace" / "plugins.json"
)

TrustLevel = Literal["verified", "community"]
PluginType = Literal["showcase", "agent", "workflow", "plugin"]


class PluginCard(BaseModel):
    id: str
    slug: str
    name: str
    type: PluginType
    version: str
    description: str
    trust_level: TrustLevel
    author: str
    tags: list[str] = Field(default_factory=list)
    example_path: str | None = None


class PluginListResponse(BaseModel):
    plugins: list[PluginCard]


def _registry_path() -> Path:
    return _REGISTRY_FILE


@lru_cache(maxsize=1)
def load_plugins() -> list[PluginCard]:
    path = _registry_path()
    if not path.is_file():
        raise FileNotFoundError(f"Marketplace registry not found: {path}")
    raw = json.loads(path.read_text(encoding="utf-8"))
    response = PluginListResponse.model_validate(raw)
    return response.plugins


def clear_plugin_cache() -> None:
    load_plugins.cache_clear()
