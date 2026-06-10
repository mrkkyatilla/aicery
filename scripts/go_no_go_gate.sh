#!/usr/bin/env bash
# E6-β2 — Go/No-Go scorecard: gate-f3 + gate-e7-p2 + gate-f6 (+ golden e2e + trace smoke)
# Target: ≥4/5 green → MVP beta tag (v0.1.0-beta)
set -uo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

API="${AICERY_API_URL:-http://localhost:8000}"
MIN_PASS="${GONOGO_MIN_PASS:-4}"
SKIP_UNIT="${GONOGO_SKIP_UNIT:-0}"

declare -a SCORE_LABELS=()
declare -a SCORE_STATUS=()

source .venv/bin/activate 2>/dev/null || {
  python3 -m venv .venv
  source .venv/bin/activate
  make install
}

record() {
  SCORE_LABELS+=("$1")
  SCORE_STATUS+=("$2")
}

run_leg() {
  local label="$1"
  shift
  echo ""
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "  $label"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  if "$@"; then
    record "$label" "PASS"
    echo "→ PASS"
    return 0
  fi
  record "$label" "FAIL"
  echo "→ FAIL"
  return 1
}

echo "== Go/No-Go: shared unit suite (once) =="
UNIT_FAILED=0
if [[ "$SKIP_UNIT" == "1" ]]; then
  echo "GONOGO_SKIP_UNIT=1 — skipping make unit"
else
  if make unit; then
    echo "unit: OK"
  else
    echo "unit: FAIL"
    UNIT_FAILED=1
  fi
fi

export GONOGO_SKIP_UNIT=1

run_leg "1 · F3 exit gate (trace/replay)" bash scripts/f3_exit_gate.sh || true
run_leg "2 · E7 P2 gate (recall + index perf)" bash scripts/e7_p2_gate.sh || true
run_leg "3 · E6 beta gate (50 concurrent + security)" bash scripts/f6_beta_gate.sh || true

if [[ "${GONOGO_P95:-0}" == "1" ]]; then
  if curl -sf "${API}/health" >/dev/null 2>&1; then
    run_leg "3b · First-token p95 gate" bash scripts/p95_gate.sh || true
  else
    record "3b · First-token p95 gate" "SKIP"
    echo "→ SKIP (API not on ${API})"
  fi
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  4 · Golden e2e (research-docs → MVP_SCOPE cite)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if curl -sf "${API}/health" >/dev/null 2>&1; then
  if bash examples/research-docs/run_e7.sh; then
    record "4 · Golden e2e" "PASS"
    echo "→ PASS"
  else
    record "4 · Golden e2e" "FAIL"
    echo "→ FAIL"
  fi
else
  record "4 · Golden e2e" "SKIP"
  echo "→ SKIP (API not on ${API} — run after gate-f6 / make up)"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  5 · Trace coverage + replay determinism (unit)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if pytest runtime/tests/unit/test_trace_replay.py::test_echo_run_has_trace \
  runtime/tests/unit/test_trace_replay.py::test_echo_trace_golden_step_count \
  runtime/tests/unit/test_trace_replay.py::test_replay_determinism_two_runs_identical_hashes -q; then
  record "5 · Trace + replay smoke" "PASS"
  echo "→ PASS"
else
  record "5 · Trace + replay smoke" "FAIL"
  echo "→ FAIL"
fi

pass=0
fail=0
skip=0
for status in "${SCORE_STATUS[@]}"; do
  case "$status" in
    PASS) pass=$((pass + 1)) ;;
    FAIL) fail=$((fail + 1)) ;;
    SKIP) skip=$((skip + 1)) ;;
  esac
done

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║           Go/No-Go scorecard (E6-β2)                         ║"
echo "╠══════════════════════════════════════════════════════════════╣"
for i in "${!SCORE_LABELS[@]}"; do
  label="${SCORE_LABELS[$i]}"
  status="${SCORE_STATUS[$i]}"
  printf "║  %-52s %5s  ║\n" "$label" "$status"
done
echo "╠══════════════════════════════════════════════════════════════╣"
printf "║  PASS: %-3d   FAIL: %-3d   SKIP: %-3d   (hedef: ≥%-2s/5)        ║\n" \
  "$pass" "$fail" "$skip" "$MIN_PASS"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo "Optional: GONOGO_P95=1 runs scripts/p95_gate.sh (first-token p95 <3s mock)."
echo "Pillar gates: make gate-f3 · make gate-e7-p2 · make gate-f6"

if [[ "${UNIT_FAILED:-0}" == "1" ]]; then
  echo ""
  echo "NO-GO: unit suite failed."
  exit 1
fi

if [[ "$pass" -ge "$MIN_PASS" && "$fail" -eq 0 ]]; then
  echo "GO — scorecard ${pass}/5 (≥${MIN_PASS} required, no failures)."
  exit 0
fi

if [[ "$pass" -ge "$MIN_PASS" ]]; then
  echo "NO-GO: ${pass}/5 green but ${fail} check(s) failed."
  exit 1
fi

echo "NO-GO: ${pass}/5 green (need ≥${MIN_PASS}, zero failures on counted legs)."
exit 1
