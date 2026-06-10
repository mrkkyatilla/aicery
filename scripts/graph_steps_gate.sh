#!/usr/bin/env bash
# T3-E6-02 — graph step limit unit gate
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

pytest runtime/tests/unit/test_graph_step_limit.py -q
echo "graph steps gate: OK"
