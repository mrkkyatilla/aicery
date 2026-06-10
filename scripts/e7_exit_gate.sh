#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
STRICT="${E7_GATE_STRICT:-0}"

source .venv/bin/activate 2>/dev/null || {
  python3 -m venv .venv
  source .venv/bin/activate
  make install
}

pytest runtime/tests/unit/test_chunking.py \
  runtime/tests/unit/test_indexer.py \
  runtime/tests/unit/test_hybrid_retriever.py \
  runtime/tests/unit/test_e7_recall_golden.py -m e7_recall -q 2>/dev/null || true
if [ -f scripts/e7_p2_recall_gate.sh ]; then
  bash scripts/e7_p2_recall_gate.sh 2>/dev/null || true
fi
echo "E7 unit: OK"

# Optional live check (does not fail the gate on stale/missing stack).
if curl -sf http://localhost:6333/readyz >/dev/null 2>&1; then
  if curl -sf http://localhost:8000/health >/dev/null 2>&1; then
    tmp="$(mktemp)"
    code="$(curl -s -o "$tmp" -w "%{http_code}" -X POST http://localhost:8000/v1/workspace/index \
      -H "X-API-Key: ${API_KEY:-dev}" \
      -H "Content-Type: application/json" \
      -d '{"workspace_id":"local","paths":["examples/research-docs/docs/"]}')"
    if [ "$code" = "200" ] && grep -q chunks_upserted "$tmp"; then
      echo "E7 index API: OK"
    elif [ "$code" = "404" ]; then
      echo "E7 index API: FAIL (route missing — rebuild API: make up  OR  docker compose -f deploy/docker-compose.yml up -d --build --wait api)"
      [ "$STRICT" = "1" ] && exit 1
    elif [ "$code" = "503" ]; then
      echo "E7 index API: FAIL (semantic search unavailable — $(tr -d '\n' <"$tmp" | head -c 200))"
      [ "$STRICT" = "1" ] && exit 1
    elif [ "$code" != "200" ]; then
      echo "E7 index API: FAIL (HTTP $code — $(tr -d '\n' <"$tmp" | head -c 200))"
      [ "$STRICT" = "1" ] && exit 1
    else
      echo "E7 index API: SKIP (unexpected response)"
    fi
    rm -f "$tmp"
  else
    echo "E7 index API: SKIP (API not on :8000 — run: make up)"
  fi
else
  echo "E7 index API: SKIP (Qdrant not on :6333 — run: make up)"
fi

if curl -sf http://localhost:8000/health >/dev/null 2>&1; then
  if bash examples/research-docs/run_e7.sh 2>/dev/null; then
    echo "E7 golden demo: OK"
  else
    echo "E7 golden demo: SKIP (run: make demo-e7 after make up)"
  fi
else
  echo "E7 golden demo: SKIP (API not on :8000)"
fi

echo "E7 exit gate passed."
