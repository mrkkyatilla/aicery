"""ASCII graph export for CLI `aicery graph` (E5 F3)."""

from __future__ import annotations

from dataclasses import dataclass

from agents.registry import _PIPELINES, _REGISTRY, list_agent_manifests


@dataclass(frozen=True)
class GraphNode:
    id: str
    detail: str = ""


@dataclass(frozen=True)
class GraphSpec:
    key: str
    title: str
    nodes: tuple[GraphNode, ...]
    kind: str = "agent"  # agent | pipeline

    def render(self) -> str:
        lines = [f"{self.title}  ({self.kind})"]
        for index, node in enumerate(self.nodes):
            is_last = index == len(self.nodes) - 1
            branch = "└─" if is_last else "├─"
            detail = f"  {node.detail}" if node.detail else ""
            lines.append(f"{branch} [{node.id}]{detail}")
        return "\n".join(lines)

    def render_mermaid(self, *, direction: str = "LR") -> str:
        lines = [f"flowchart {direction}"]
        node_ids = [n.id for n in self.nodes]
        for node in self.nodes:
            label = node.id
            if node.detail:
                label = f"{node.id}<br/>{node.detail}"
            lines.append(f'  {node.id}["{label}"]')
        for index in range(len(node_ids) - 1):
            lines.append(f"  {node_ids[index]} --> {node_ids[index + 1]}")
        return "\n".join(lines)


_SPECS: dict[str, GraphSpec] = {
    "echo": GraphSpec(
        key="echo",
        title="echo",
        kind="agent",
        nodes=(
            GraphNode("llm", "provider.stream"),
        ),
    ),
    "research": GraphSpec(
        key="research",
        title="research",
        kind="agent",
        nodes=(
            GraphNode("research", "extract path from input"),
            GraphNode("tool", "read_file"),
            GraphNode("llm", "provider.stream"),
        ),
    ),
    "research-chain": GraphSpec(
        key="research-chain",
        title="research-chain",
        kind="pipeline",
        nodes=(
            GraphNode("planner", "search_workspace"),
            GraphNode("executor", "read_file"),
            GraphNode("summarizer", "provider.complete"),
        ),
    ),
}


def list_graph_keys() -> list[str]:
    keys = set(_REGISTRY) | set(_PIPELINES)
    return sorted(keys)


def resolve_graph_key(name: str) -> str:
    normalized = name.strip()
    if normalized in _SPECS:
        return normalized
    if normalized in _PIPELINES:
        return normalized
    if normalized in _REGISTRY:
        return normalized
    raise KeyError(normalized)


def render_graph(name: str, *, format: str = "ascii") -> str:
    key = resolve_graph_key(name)
    spec = _SPECS.get(key)
    if spec is None:
        manifest = next((a for a in list_agent_manifests() if a["id"] == key), None)
        tools = ", ".join(manifest["tools"]) if manifest else "unknown"
        if format == "mermaid":
            safe = key.replace("-", "_")
            return f'flowchart LR\n  {safe}["{key}<br/>tools: {tools or "none"}"]'
        return f"{key}  (agent)\n└─ [runtime]  tools: {tools or 'none'}"
    if format == "mermaid":
        return spec.render_mermaid()
    return spec.render()


def render_all_graphs(*, format: str = "ascii") -> str:
    blocks = [render_graph(key, format=format) for key in list_graph_keys()]
    separator = "\n\n" if format == "ascii" else "\n\n---\n\n"
    return separator.join(blocks)


def render_graph_mermaid(name: str) -> str:
    return render_graph(name, format="mermaid")
