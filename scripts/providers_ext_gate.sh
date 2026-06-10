#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
pytest runtime/tests/unit/test_groq_provider.py \
  runtime/tests/unit/test_anthropic_provider.py \
  runtime/tests/unit/test_openai_provider.py \
  runtime/tests/unit/test_policy_resolver.py -q
echo "gate-providers-ext OK"
