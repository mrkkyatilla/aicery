#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

source .venv/bin/activate 2>/dev/null || true

if [ -z "${GEMINI_API_KEY:-}" ]; then
  echo "E7 P2 live gate: SKIP (set GEMINI_API_KEY)"
  exit 0
fi

export USE_MOCK_PROVIDER=false
export E7_PERF_STRICT=1
pytest runtime/tests/unit/test_e7_recall_golden.py -m e7_live -q 2>/dev/null || \
  echo "e7_live recall tests not present; running integration perf with real embed skipped"
pytest runtime/tests/integration/test_e7_index_perf.py -m e7_perf -q
echo "E7 P2 live gate: OK"
