#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "== MOD-DRIFT: unit tests =="
pytest runtime/tests/unit/test_drift_evaluator.py -q

echo "== MOD-DRIFT: soft report =="
python3 - <<'PY'
import json
from runtime.services.drift_evaluator import evaluate_drift

report = evaluate_drift()
payload = report.to_dict()
assert payload["regressions"] >= 0
assert payload["total"] >= 3
print(json.dumps({"total": payload["total"], "regressions": payload["regressions"]}))
PY

echo "== MOD-DRIFT gate OK (soft exit 0) =="
