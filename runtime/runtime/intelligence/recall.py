from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, Field

from runtime.intelligence.indexer import WorkspaceIndexer
from runtime.intelligence.retriever import HybridRetriever


class GoldenQuery(BaseModel):
    query: str
    expected_paths: list[str] = Field(default_factory=list)
    workspace_paths: list[str] = Field(default_factory=lambda: ["guide/"])


class RecallReport(BaseModel):
    mean_recall_at_k: float
    k: int
    queries_evaluated: int
    per_query: list[dict]


def recall_at_k(hits: list[dict], expected_paths: list[str], k: int = 5) -> float:
    if not expected_paths:
        return 0.0
    top = hits[:k]
    found = {h.get("file", "") for h in top}
    for expected in expected_paths:
        norm = expected.replace("\\", "/")
        for hit_path in found:
            if hit_path == norm or hit_path.endswith("/" + norm) or norm.endswith(hit_path):
                return 1.0
            if norm in hit_path or hit_path in norm:
                return 1.0
    return 0.0


def load_golden_queries(path: Path) -> list[GoldenQuery]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return [GoldenQuery.model_validate(item) for item in data]


def evaluate_golden_set(
    workspace_id: str,
    workspace_root: str,
    queries: list[GoldenQuery],
    *,
    memory,
    k: int = 5,
) -> RecallReport:
    root = Path(workspace_root).resolve()
    indexer = WorkspaceIndexer(memory, str(root))
    paths = sorted({p for q in queries for p in q.workspace_paths})
    indexer.index(workspace_id, paths or ["guide/"])

    retriever = HybridRetriever(memory, workspace_root=str(root))
    per_query: list[dict] = []
    scores: list[float] = []
    for item in queries:
        out = retriever.search(workspace_id, item.query, top_k=k)
        score = recall_at_k(out.get("hits", []), item.expected_paths, k=k)
        scores.append(score)
        per_query.append(
            {
                "query": item.query,
                "recall_at_k": score,
                "source": out.get("source"),
                "hits": out.get("hits", [])[:k],
            }
        )
    mean = sum(scores) / len(scores) if scores else 0.0
    return RecallReport(
        mean_recall_at_k=mean,
        k=k,
        queries_evaluated=len(scores),
        per_query=per_query,
    )
