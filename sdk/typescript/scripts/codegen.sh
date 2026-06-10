#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OPENAPI="${ROOT}/../../runtime/openapi/openapi.v1.json"
OUT="${ROOT}/src/generated/openapi.ts"
mkdir -p "$(dirname "$OUT")"
npx openapi-typescript "$OPENAPI" -o "$OUT"
echo "codegen OK: $OUT"
