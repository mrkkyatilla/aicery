from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

DEFAULT_GOLDEN = (
    Path(__file__).resolve().parents[2] / "data" / "drift" / "golden_runs.json"
)


@dataclass
class DriftCaseResult:
    case_id: str
    score: float
    passed: bool
    expected_keywords: list[str]
    actual_output: str
    regression: bool


@dataclass
class DriftReport:
    baseline: str
    total: int
    passed: int
    regressions: int
    cases: list[DriftCaseResult]

    def to_dict(self) -> dict:
        return {
            "baseline": self.baseline,
            "total": self.total,
            "passed": self.passed,
            "regressions": self.regressions,
            "cases": [
                {
                    "case_id": c.case_id,
                    "score": c.score,
                    "passed": c.passed,
                    "expected_keywords": c.expected_keywords,
                    "actual_output": c.actual_output,
                    "regression": c.regression,
                }
                for c in self.cases
            ],
        }


def harvest_golden_runs(path: Path | str | None = None) -> list[dict]:
    golden_path = Path(path) if path else DEFAULT_GOLDEN
    return json.loads(golden_path.read_text(encoding="utf-8"))


def _keyword_overlap(expected: list[str], actual: str) -> float:
    if not expected:
        return 1.0
    text = actual.lower()
    hits = sum(1 for kw in expected if kw.lower() in text)
    return hits / len(expected)


def _mock_replay_output(case: dict) -> str:
    """Fixture replay: use recorded LLM output_preview (gate uses mock only)."""
    for step in case.get("trace_steps", []):
        if step.get("type") == "llm" and step.get("output_preview"):
            return str(step["output_preview"])
    return ""


def replay_diff(case: dict) -> DriftCaseResult:
    run_id = case.get("id", "golden")
    actual = _mock_replay_output(case)
    keywords = list(case.get("expected_keywords", []))
    score = _keyword_overlap(keywords, actual)
    threshold = float(case.get("pass_threshold", 0.6))
    passed = score >= threshold
    expect_regression = bool(case.get("expect_regression", False))
    regression = expect_regression or not passed
    return DriftCaseResult(
        case_id=run_id,
        score=round(score, 3),
        passed=passed,
        expected_keywords=keywords,
        actual_output=actual,
        regression=regression if not passed else expect_regression,
    )


def evaluate_drift(*, baseline: Path | str | None = None) -> DriftReport:
    cases_raw = harvest_golden_runs(baseline)
    results: list[DriftCaseResult] = []
    for case in cases_raw:
        if case.get("expect_regression"):
            keywords = case.get("expected_keywords", [])
            actual = case["trace_steps"][0].get("output_preview", "")
            score = _keyword_overlap(keywords, actual)
            passed = score >= float(case.get("pass_threshold", 0.6))
            results.append(
                DriftCaseResult(
                    case_id=case["id"],
                    score=round(score, 3),
                    passed=passed,
                    expected_keywords=keywords,
                    actual_output=actual,
                    regression=not passed,
                )
            )
            continue
        results.append(replay_diff(case))

    passed = sum(1 for r in results if r.passed)
    regressions = sum(1 for r in results if r.regression)
    baseline_label = str(baseline or DEFAULT_GOLDEN)
    return DriftReport(
        baseline=baseline_label,
        total=len(results),
        passed=passed,
        regressions=regressions,
        cases=results,
    )


def format_report(report: DriftReport) -> str:
    return json.dumps(report.to_dict(), indent=2, ensure_ascii=False)
