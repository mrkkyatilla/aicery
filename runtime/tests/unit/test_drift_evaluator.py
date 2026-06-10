import json
from pathlib import Path

from runtime.services.drift_evaluator import evaluate_drift, harvest_golden_runs, replay_diff

GOLDEN = Path(__file__).resolve().parents[2] / "data" / "drift" / "golden_runs.json"


def test_harvest_golden_runs():
    cases = harvest_golden_runs(GOLDEN)
    assert len(cases) >= 3


def test_replay_diff_passing_case():
    cases = harvest_golden_runs(GOLDEN)
    good = next(c for c in cases if c["id"] == "research-refund-1")
    result = replay_diff(good)
    assert result.passed
    assert result.score >= 0.6


def test_replay_diff_regression_case():
    cases = harvest_golden_runs(GOLDEN)
    bad = next(c for c in cases if c["id"] == "broken-prompt-case")
    result = replay_diff(bad)
    assert result.score < 0.6
    assert result.regression


def test_evaluate_drift_report():
    report = evaluate_drift(baseline=GOLDEN)
    assert report.total >= 3
    assert report.regressions >= 0
    payload = report.to_dict()
    assert "cases" in payload
    json.dumps(payload)
