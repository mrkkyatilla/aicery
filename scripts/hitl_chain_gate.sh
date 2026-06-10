#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
pytest agents/tests/test_chain_hitl_interrupt.py runtime/tests/unit/test_hitl_research_chain.py -q
