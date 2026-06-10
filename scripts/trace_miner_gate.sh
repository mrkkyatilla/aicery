#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "== MOD-TRACE-MINER: unit tests =="
pytest runtime/tests/unit/test_trace_miner.py -q

echo "== MOD-TRACE-MINER: fixture report =="
python3 - <<'PY'
import json
from pathlib import Path

import jsonschema

from core.domain.trace import TraceStep
from runtime.services.trace_miner import analyze_steps, load_report_schema

raw = json.loads(Path("runtime/data/trace_miner/fixture_steps.json").read_text())
steps = [TraceStep.model_validate(item) for item in raw["steps"]]
report = analyze_steps(
    steps,
    agent_id=raw["agent_id"],
    min_runs=3,
    known_nodes=raw.get("known_nodes"),
)
payload = report.to_dict()
jsonschema.validate(payload, load_report_schema())
assert "dead_nodes" in payload
assert "visit_pct" in payload
assert "dead-step" in payload["dead_nodes"]
print(json.dumps({"dead_nodes": payload["dead_nodes"], "visit_pct": payload["visit_pct"]}))
PY

echo "== MOD-TRACE-MINER gate OK =="
