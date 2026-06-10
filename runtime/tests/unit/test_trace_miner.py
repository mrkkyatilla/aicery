import json
from pathlib import Path

import jsonschema

from core.domain.trace import TraceStep, TraceStepType
from runtime.services.trace_miner import analyze_steps, load_report_schema

SCHEMA = load_report_schema()
FIXTURE = Path(__file__).resolve().parents[2] / "data" / "trace_miner" / "fixture_steps.json"


def _step(run_id: str, name: str, node: str, *, tool: bool = False) -> TraceStep:
    if tool:
        return TraceStep(
            run_id=run_id,
            type=TraceStepType.TOOL,
            name=name,
            metadata={"duration_ms": 5},
        )
    return TraceStep(
        run_id=run_id,
        type=TraceStepType.AGENT,
        name=name,
        metadata={"node": node, "usage": {"total_tokens": 42}},
    )


def test_analyze_steps_report_schema():
    steps = []
    for i in range(12):
        rid = f"run-{i % 6}"
        steps.append(_step(rid, "research.plan", "plan"))
        steps.append(_step(rid, "research.answer", "answer"))
        if i % 3 == 0:
            steps.append(_step(rid, "search_workspace", "search_workspace", tool=True))

    report = analyze_steps(
        steps,
        agent_id="research",
        min_runs=10,
        known_nodes=["plan", "answer", "unused-node"],
    )
    payload = report.to_dict()
    jsonschema.validate(payload, SCHEMA)
    assert "plan" in payload["visit_pct"]
    assert "unused-node" in payload["dead_nodes"]
    assert payload["run_count"] == 6


def test_fixture_file_if_present():
    if not FIXTURE.is_file():
        return
    raw = json.loads(FIXTURE.read_text())
    steps = [TraceStep.model_validate(item) for item in raw["steps"]]
    report = analyze_steps(steps, agent_id=raw.get("agent_id", "research"), min_runs=5)
    jsonschema.validate(report.to_dict(), SCHEMA)
