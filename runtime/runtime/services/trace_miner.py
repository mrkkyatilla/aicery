from __future__ import annotations

import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

from core.domain.trace import TraceStep, TraceStepType
from runtime.adapters.db.trace_repository import TraceRepository

SCHEMA_PATH = (
    Path(__file__).resolve().parents[2] / "data" / "trace_miner" / "report_schema.json"
)


@dataclass
class TraceMinerReport:
    agent_id: str
    min_runs: int
    run_count: int
    low_confidence: bool
    nodes: list[dict]
    dead_nodes: list[str]
    visit_pct: dict[str, float]
    avg_tokens: float
    recommendations: list[str]

    def to_dict(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "min_runs": self.min_runs,
            "run_count": self.run_count,
            "low_confidence": self.low_confidence,
            "nodes": self.nodes,
            "dead_nodes": self.dead_nodes,
            "visit_pct": self.visit_pct,
            "avg_tokens": self.avg_tokens,
            "recommendations": self.recommendations,
        }


def _node_name(step: TraceStep) -> str | None:
    if step.type == TraceStepType.AGENT:
        return step.metadata.get("node") or step.name
    if step.type == TraceStepType.TOOL:
        return f"tool:{step.name}"
    if step.type == TraceStepType.LLM:
        return f"llm:{step.name}"
    return step.name or None


def _extract_tokens(step: TraceStep) -> int:
    usage = (step.metadata or {}).get("usage") or {}
    if isinstance(usage, dict):
        total = usage.get("total_tokens")
        if isinstance(total, int):
            return total
    return 0


def analyze_steps(
    steps: list[TraceStep],
    *,
    agent_id: str,
    min_runs: int = 10,
    known_nodes: list[str] | None = None,
) -> TraceMinerReport:
    run_ids = {s.run_id for s in steps}
    run_count = len(run_ids)
    visits: Counter[str] = Counter()
    tokens_per_run: dict[str, int] = defaultdict(int)

    for step in steps:
        name = _node_name(step)
        if not name:
            continue
        visits[name] += 1
        tokens_per_run[step.run_id] += _extract_tokens(step)

    total_visits = sum(visits.values()) or 1
    visit_pct = {name: round(count / total_visits * 100, 2) for name, count in visits.items()}
    nodes = [
        {"name": name, "visits": count, "visit_pct": visit_pct[name]}
        for name, count in sorted(visits.items(), key=lambda x: (-x[1], x[0]))
    ]

    observed = set(visits.keys())
    catalog = set(known_nodes or [])
    dead_nodes = sorted(catalog - observed) if catalog else []

    avg_tokens = 0.0
    if tokens_per_run:
        avg_tokens = round(sum(tokens_per_run.values()) / len(tokens_per_run), 2)

    recommendations: list[str] = []
    if run_count < min_runs:
        recommendations.append(
            f"Sample size {run_count} below min_runs={min_runs}; treat visit percentages as low confidence."
        )
    for node in dead_nodes:
        recommendations.append(f"Node '{node}' never visited — consider removing or fixing routing.")

    return TraceMinerReport(
        agent_id=agent_id,
        min_runs=min_runs,
        run_count=run_count,
        low_confidence=run_count < min_runs,
        nodes=nodes,
        dead_nodes=dead_nodes,
        visit_pct=visit_pct,
        avg_tokens=avg_tokens,
        recommendations=recommendations,
    )


def analyze_from_repository(
    repo: TraceRepository,
    *,
    agent_id: str,
    run_ids: list[str],
    min_runs: int = 10,
    known_nodes: list[str] | None = None,
) -> TraceMinerReport:
    steps: list[TraceStep] = []
    for run_id in run_ids:
        steps.extend(repo.list_by_run(run_id))
    return analyze_steps(
        steps,
        agent_id=agent_id,
        min_runs=min_runs,
        known_nodes=known_nodes,
    )


def load_report_schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
