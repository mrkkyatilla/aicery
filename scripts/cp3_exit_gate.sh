#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
source .venv/bin/activate 2>/dev/null || true
pip install -q -e "./services/gateway[dev]" 2>/dev/null || true
make gateway-unit
echo "CP-3 exit gate: gateway unit tests passed"
