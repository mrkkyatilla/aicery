#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
pytest runtime/tests/unit/test_otel_export.py services/gateway/tests/test_otel_proxy.py -q
