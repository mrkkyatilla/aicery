from pathlib import Path

import pytest

from runtime.intelligence.memory_inmemory import InMemorySemanticMemory
from runtime.intelligence.recall import evaluate_golden_set, load_golden_queries

REPO_ROOT = Path(__file__).resolve().parents[3]
GOLDEN_JSON = REPO_ROOT / "tests" / "fixtures" / "e7_golden" / "recall_queries.json"
CORPUS_ROOT = REPO_ROOT / "tests" / "fixtures" / "e7_golden"


@pytest.mark.e7_recall
def test_golden_recall_at_5_meets_threshold(monkeypatch):
    monkeypatch.setenv("USE_MOCK_PROVIDER", "true")
    queries = load_golden_queries(GOLDEN_JSON)
    memory = InMemorySemanticMemory(vector_size=768)
    report = evaluate_golden_set(
        "e7-golden",
        str(CORPUS_ROOT),
        queries,
        memory=memory,
        k=5,
    )
    assert report.queries_evaluated >= 5
    assert report.mean_recall_at_k >= 0.6, report.model_dump()
