from pathlib import Path

from core.ports.semantic_memory import Chunk
from runtime.intelligence.indexer import WorkspaceIndexer


class _MemoryStub:
    def __init__(self) -> None:
        self.chunks: list[Chunk] = []

    def upsert_chunks(self, chunks: list[Chunk]) -> None:
        self.chunks.extend(chunks)


def test_workspace_indexer_counts_files_and_chunks(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("USE_MOCK_PROVIDER", "true")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "a.md").write_text("hello semantic world\n" * 50)
    (docs / "b.py").write_text("print('x')\n")

    memory = _MemoryStub()
    indexer = WorkspaceIndexer(memory, str(tmp_path))  # type: ignore[arg-type]
    result = indexer.index("test-ws", ["docs/"])

    assert result.files_indexed == 2
    assert result.chunks_upserted == len(memory.chunks)
    assert result.chunks_upserted >= 2
    paths = {c.path for c in memory.chunks}
    assert "docs/a.md" in paths
    assert "docs/b.py" in paths


def test_workspace_indexer_missing_path_raises(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("USE_MOCK_PROVIDER", "true")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    memory = _MemoryStub()
    indexer = WorkspaceIndexer(memory, str(tmp_path))  # type: ignore[arg-type]
    try:
        indexer.index("test-ws", ["no-such-dir/"])
        assert False, "expected FileNotFoundError"
    except FileNotFoundError as exc:
        assert "no-such-dir" in str(exc)
