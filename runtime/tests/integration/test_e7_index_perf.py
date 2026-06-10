from pathlib import Path

import pytest

from runtime.intelligence.indexer import WorkspaceIndexer
from runtime.intelligence.memory_inmemory import InMemorySemanticMemory

REPO_ROOT = Path(__file__).resolve().parents[3]
CORPUS_DIR = REPO_ROOT / "tests" / "fixtures" / "e7_perf" / "corpus"
GENERATOR = REPO_ROOT / "tests" / "fixtures" / "e7_perf" / "generate_corpus.py"
MAX_DURATION_MS = 120_000
FILE_COUNT = 100


@pytest.fixture(scope="module")
def perf_corpus(tmp_path_factory):
    out = tmp_path_factory.mktemp("e7_perf_corpus")
    import subprocess
    import sys

    subprocess.run(
        [sys.executable, str(GENERATOR), "--out", str(out), "--count", str(FILE_COUNT)],
        check=True,
    )
    return out


@pytest.mark.e7_perf
def test_index_100_files_under_120s(monkeypatch, perf_corpus):
    monkeypatch.setenv("USE_MOCK_PROVIDER", "true")
    memory = InMemorySemanticMemory(vector_size=768)
    indexer = WorkspaceIndexer(memory, str(perf_corpus))
    result = indexer.index("e7-perf", ["./"])
    assert result.files_indexed == FILE_COUNT
    assert result.chunks_upserted > 0
    assert result.duration_ms < MAX_DURATION_MS, (
        f"index took {result.duration_ms}ms, limit {MAX_DURATION_MS}ms"
    )
