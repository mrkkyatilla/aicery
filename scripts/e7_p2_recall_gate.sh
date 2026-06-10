#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
source .venv/bin/activate 2>/dev/null || true
pytest runtime/tests/unit/test_e7_recall_golden.py -m e7_recall -q
echo "E7 P2 recall gate: OK"
