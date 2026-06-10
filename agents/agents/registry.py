from collections.abc import Callable
from pathlib import Path

import yaml

from agents.graphs.chain_research import build_research_chain_graph
from agents.graphs.echo import build_echo_graph
from agents.graphs.hitl_demo import build_hitl_demo_graph
from agents.graphs.research import build_research_graph
from agents.plugin_paths import get_plugin_roots
from core.domain.error_codes import ErrorCode
from core.domain.run import Run
from core.ports.provider import ProviderPort
from core.ports.tool_executor import ToolExecutorPort

GraphBuilder = Callable[[ProviderPort, ToolExecutorPort | None, Run | None], object]

_REGISTRY: dict[str, GraphBuilder] = {
    "echo": build_echo_graph,
    "research": build_research_graph,
    "hitl-demo": build_hitl_demo_graph,
}

_PLUGIN_REGISTRY: dict[str, GraphBuilder] = {}

_PIPELINES: dict[str, GraphBuilder] = {
    "research-chain": build_research_chain_graph,
}


def register_plugin_agent(agent_id: str, builder: GraphBuilder) -> None:
    _PLUGIN_REGISTRY[agent_id] = builder

MANIFESTS_DIR = Path(__file__).resolve().parent.parent / "builtins" / "manifests"


class UnknownAgentError(Exception):
    error_code = ErrorCode.UNKNOWN_AGENT


def get_graph_builder(agent_id: str, *, pipeline: str | None = None) -> GraphBuilder:
    if pipeline:
        builder = _PIPELINES.get(pipeline)
        if builder is None:
            raise UnknownAgentError(f"Unknown pipeline: {pipeline}")
        return builder
    builder = _REGISTRY.get(agent_id) or _PLUGIN_REGISTRY.get(agent_id)
    if builder is None:
        raise UnknownAgentError(f"Unknown agent: {agent_id}")
    return builder


def resolve_run_target(run: Run) -> tuple[str, str | None]:
    """Return (agent_id, pipeline_id) for orchestration."""
    if run.pipeline_id:
        return run.agent_id or "research", run.pipeline_id
    return run.agent_id, None


def list_agent_manifests() -> list[dict]:
    agents: list[dict] = []
    if not MANIFESTS_DIR.is_dir():
        return agents
    for path in sorted(MANIFESTS_DIR.glob("*.yaml")):
        data = yaml.safe_load(path.read_text())
        if isinstance(data, dict):
            agents.append(
                {
                    "id": data.get("id", path.stem),
                    "version": data.get("version", "1.0.0"),
                    "tools": data.get("tools", []),
                    "description": data.get("description", ""),
                    "pipelines": data.get("pipelines", []),
                }
            )
    seen_ids = {a["id"] for a in agents}
    for path in _iter_plugin_manifest_files():
        data = yaml.safe_load(path.read_text())
        if not isinstance(data, dict):
            continue
        agent_id = data.get("id", path.stem)
        if agent_id in seen_ids:
            continue
        agents.append(
            {
                "id": agent_id,
                "version": data.get("version", "1.0.0"),
                "tools": data.get("tools", []),
                "description": data.get("description", ""),
                "pipelines": data.get("pipelines", []),
            }
        )
        seen_ids.add(agent_id)
    for pipeline_id in _PIPELINES:
        found = any(pipeline_id in a.get("pipelines", []) for a in agents)
        if not found:
            agents.append(
                {
                    "id": "research",
                    "version": "1.0.0",
                    "tools": ["read_file", "list_files", "search_workspace"],
                    "description": "Research pipeline",
                    "pipelines": [pipeline_id],
                }
            )
    return agents


def _iter_plugin_manifest_files() -> list[Path]:
    files: list[Path] = []
    for root in get_plugin_roots():
        agents_dir = root / "agents"
        if agents_dir.is_dir():
            files.extend(sorted(agents_dir.glob("*.yaml")))
    return files
