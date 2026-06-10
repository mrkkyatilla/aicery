"""T3-E7-03 — semantic disabled still allows grep search path."""

import pytest

from runtime.intelligence.retriever import HybridRetriever


@pytest.mark.integration
def test_hybrid_grep_only_when_memory_none(tmp_path, monkeypatch):
    monkeypatch.setenv("SEMANTIC_SEARCH_ENABLED", "false")
    doc = tmp_path / "notes.md"
    doc.write_text("FALLBACK_UNIQUE_E7 token for grep-only retrieval.\n", encoding="utf-8")
    retriever = HybridRetriever(None, workspace_root=str(tmp_path))
    out = retriever.search("local", "FALLBACK_UNIQUE_E7", top_k=5)
    assert out["source"] == "grep"
    assert any("notes.md" in h.get("file", "") for h in out["hits"])
