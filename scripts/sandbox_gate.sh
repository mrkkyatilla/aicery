#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
COMPOSE="docker compose -f deploy/docker-compose.yml --profile sandbox"

echo "== SANDBOX: unit tests =="
pytest runtime/tests/unit/test_execute_code.py -q

echo "== SANDBOX: sidecar smoke =="
_RUNNER_PID=""
_cleanup_runner() {
  if [[ -n "${_RUNNER_PID}" ]]; then
    kill "${_RUNNER_PID}" 2>/dev/null || true
  fi
}
trap _cleanup_runner EXIT

if ! curl -sf "http://localhost:8091/health" >/dev/null 2>&1; then
  if $COMPOSE up -d --build --wait sandbox-runner --remove-orphans 2>/dev/null; then
    :
  else
    echo "docker unavailable — starting local sandbox-runner"
    python3 deploy/sandbox-runner/runner.py &
    _RUNNER_PID=$!
    for _ in $(seq 1 20); do
      curl -sf "http://localhost:8091/health" >/dev/null 2>&1 && break
      sleep 0.25
    done
  fi
fi

export EXECUTE_CODE_ENABLED=true
export SANDBOX_RUNNER_URL=http://localhost:8091
python3 - <<'PY'
import os
os.environ["EXECUTE_CODE_ENABLED"] = "true"
os.environ["SANDBOX_RUNNER_URL"] = "http://localhost:8091"
from tools.builtins.execute_code import execute_code
result = execute_code("print(1)")
assert result["stdout"].strip() == "1", result
print("execute_code stdout OK")
PY

echo "== SANDBOX: API has no subprocess for execute_code =="
python3 - <<'PY'
import inspect
from tools.builtins import execute_code as mod
src = inspect.getsource(mod.execute_code)
assert "import subprocess" not in src
assert "subprocess.run" not in src
print("no subprocess in execute_code stub OK")
PY

echo "== SANDBOX gate OK =="
