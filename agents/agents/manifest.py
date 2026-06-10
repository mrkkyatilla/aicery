from functools import lru_cache
from pathlib import Path

import yaml

from agents.plugin_paths import get_plugin_roots
from core.domain.error_codes import ErrorCode
from core.domain.provider_policy import ModelRef, ProviderPolicy

MANIFESTS_DIR = Path(__file__).resolve().parent.parent / "builtins" / "manifests"


def _plugin_manifest_path(agent_id: str) -> Path | None:
    for root in get_plugin_roots():
        path = root / "agents" / f"{agent_id}.yaml"
        if path.is_file():
            return path
    return None


def _iter_plugin_manifest_files() -> list[Path]:
    files: list[Path] = []
    for root in get_plugin_roots():
        agents_dir = root / "agents"
        if not agents_dir.is_dir():
            continue
        files.extend(sorted(agents_dir.glob("*.yaml")))
    return files


class AgentManifestError(Exception):
    error_code = ErrorCode.AGENT_MANIFEST_ERROR


@lru_cache
def load_manifest(agent_id: str) -> dict:
    path = MANIFESTS_DIR / f"{agent_id}.yaml"
    if not path.is_file():
        plugin_path = _plugin_manifest_path(agent_id)
        if plugin_path is None:
            raise AgentManifestError(f"Manifest not found: {agent_id}")
        path = plugin_path
    data = yaml.safe_load(path.read_text())
    if not isinstance(data, dict):
        raise AgentManifestError(f"Invalid manifest: {agent_id}")
    return data


def _normalize_tool_entry(entry: object, agent_id: str) -> tuple[str, bool]:
    if isinstance(entry, str):
        return entry, False
    if isinstance(entry, dict):
        name = entry.get("name")
        if not name:
            raise AgentManifestError(f"Tool entry missing name in manifest: {agent_id}")
        return str(name), bool(entry.get("requires_approval", False))
    raise AgentManifestError(f"Invalid tool entry in manifest: {agent_id}")


def get_allowed_tools(agent_id: str) -> list[str]:
    manifest = load_manifest(agent_id)
    tools = manifest.get("tools") or []
    names: list[str] = []
    for entry in tools:
        name, _ = _normalize_tool_entry(entry, agent_id)
        names.append(name)
    return names


def tool_requires_approval(agent_id: str, tool_name: str) -> bool:
    manifest = load_manifest(agent_id)
    tools = manifest.get("tools") or []
    for entry in tools:
        name, requires = _normalize_tool_entry(entry, agent_id)
        if name == tool_name:
            return requires
    return False


def get_model_policy(agent_id: str) -> ProviderPolicy | None:
    manifest = load_manifest(agent_id)
    llm = _model_ref_from_block(manifest.get("model"))
    embedding = _model_ref_from_block(manifest.get("embedding"))
    if llm is None and embedding is None:
        return None
    return ProviderPolicy(llm=llm, embedding=embedding)


def _model_ref_from_block(block: object) -> ModelRef | None:
    if not isinstance(block, dict):
        return None
    provider = block.get("provider")
    if not provider:
        return None
    return ModelRef(provider=str(provider).lower(), model=block.get("name"))
