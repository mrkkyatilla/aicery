#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
pytest runtime/tests/unit/test_hitl_coordinator.py \
  agents/tests/test_chain_hitl_interrupt.py \
  runtime/tests/unit/test_hitl.py \
  runtime/tests/unit/test_hitl_research_chain.py \
  runtime/tests/unit/test_sse_suspended.py \
  runtime/tests/unit/test_hitl_sweeper.py \
  services/gateway/tests/test_proxy_resume.py \
  -q
