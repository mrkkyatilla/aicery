#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
pytest services/gateway/tests/test_jwt_auth.py \
  services/gateway/tests/test_jwt_proxy.py \
  services/gateway/tests/test_rate_limit.py \
  services/gateway/tests/test_max_graph_steps.py \
  runtime/tests/unit/test_graph_policy_context.py \
  runtime/tests/unit/test_rate_limit_gateway_only.py -q
echo "gate-gateway-policy OK"
