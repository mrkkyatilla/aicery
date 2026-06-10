#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "== MOD-PRIVACY: unit tests =="
pytest runtime/tests/unit/test_privacy_proxy.py -q

echo "== MOD-PRIVACY: golden PII mask (no plaintext outbound) =="
python3 - <<'PY'
import json
from pathlib import Path
from runtime.adapters.providers.privacy_proxy import PrivacyVault, mask_text

golden = json.loads(Path("runtime/data/privacy/golden_pii.json").read_text())
for case in golden:
    vault = PrivacyVault()
    masked = mask_text(case["input"], vault)
    for forbidden in case.get("must_not_contain", []):
        assert forbidden not in masked, f"{case['id']}: found {forbidden!r} in masked text"
print("golden PII OK")
PY

echo "== MOD-PRIVACY gate OK =="
