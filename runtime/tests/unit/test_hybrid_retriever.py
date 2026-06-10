from pathlib import Path

from runtime.intelligence.retriever import HybridRetriever, chunks_to_hits
from tools.builtins.search_workspace import register_semantic_backend, search_workspace


def test_chunks_to_hits_snippet():
    from core.ports.semantic_memory import Chunk

    hits = chunks_to_hits(
        [Chunk(chunk_id="1", workspace_id="w", path="a.md", text="line one\nline two", metadata={"chunk_index": 0})]
    )
    assert hits[0]["file"] == "a.md"
    assert hits[0]["line"] == 1


def test_hybrid_retriever_grep_only_when_no_memory(tmp_path: Path):
    (tmp_path / "needle.md").write_text("MVP scope is defined here\n")
    retriever = HybridRetriever(None, workspace_root=str(tmp_path))
    out = retriever.search("local", "MVP scope", top_k=5)
    assert out["source"] == "grep"
    assert any("needle.md" in h["file"] for h in out["hits"])


def test_search_workspace_semantic_backend_failure_falls_back(tmp_path: Path):
    (tmp_path / "fallback.txt").write_text("unique grep token xyz\n")

    def _broken(**_kwargs):
        raise RuntimeError("qdrant down")

    register_semantic_backend(_broken)
    try:
        result = search_workspace("unique grep token", workspace_root=str(tmp_path), max_hits=5)
        assert any("fallback.txt" in h["file"] for h in result["hits"])
    finally:
        register_semantic_backend(None)  # type: ignore[arg-type]
