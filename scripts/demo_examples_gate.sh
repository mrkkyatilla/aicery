#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
COMPOSE="docker compose -f deploy/docker-compose.yml"

export HITL_ENABLED=false
export USE_MOCK_PROVIDER=true
export RATE_LIMIT_ENABLED=false

echo "== Demo examples gate: ensuring API (HITL off, mock provider) =="
$COMPOSE up -d --wait postgres redis nats qdrant --remove-orphans
$COMPOSE run --rm --build migrate
DOCKER_BUILDKIT=1 $COMPOSE up -d --build --wait api --remove-orphans

bash examples/workspace-analyst/scripts/demo.sh
bash examples/stock-advisor/scripts/demo.sh
bash examples/runbook-agent/scripts/demo.sh
bash examples/compliance-scan/scripts/demo.sh
bash examples/support-drafter/scripts/demo.sh
bash examples/sales-research/scripts/demo.sh
echo "gate-demo-examples OK"
