#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
export API_KEY=dev
python -m pytest runtime/tests/unit/test_mock_stream.py runtime/tests/unit/test_sse.py -q
