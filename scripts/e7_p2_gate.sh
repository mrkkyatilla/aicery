#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

source .venv/bin/activate 2>/dev/null || true

bash scripts/e7_p2_recall_gate.sh
pytest runtime/tests/unit/test_chunking.py \
  runtime/tests/unit/test_indexer.py \
  runtime/tests/unit/test_hybrid_retriever.py \
  runtime/tests/unit/test_e7_recall_golden.py \
  runtime/tests/unit/test_minio_blob_store.py -q
pytest runtime/tests/integration/test_e7_index_perf.py -m e7_perf -q
echo "E7 P2 gate: OK"
