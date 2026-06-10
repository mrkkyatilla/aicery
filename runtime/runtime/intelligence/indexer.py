from __future__ import annotations

import hashlib
import time
from pathlib import Path

from pydantic import BaseModel

from core.ports.semantic_memory import Chunk
from runtime.config import Settings
from runtime.intelligence.chunking import chunk_text, is_text_file
from runtime.intelligence.embeddings import get_embedder
from runtime.intelligence.qdrant_memory import QdrantSemanticMemory


class IndexResult(BaseModel):
    workspace_id: str
    files_indexed: int
    chunks_upserted: int
    duration_ms: int


class WorkspaceIndexer:
    def __init__(
        self,
        memory: QdrantSemanticMemory,
        workspace_root: str,
        *,
        blob_store=None,
    ) -> None:
        self._memory = memory
        self._workspace_root = Path(workspace_root).resolve()
        self._embedder = get_embedder()
        self._blob_store = blob_store
        settings = Settings()
        self._batch_size = settings.index_embed_batch_size

    def index(self, workspace_id: str, paths: list[str]) -> IndexResult:
        started = time.monotonic()
        files_indexed = 0
        chunks_upserted = 0
        batch: list[Chunk] = []
        batch_size = self._batch_size

        def flush() -> None:
            nonlocal chunks_upserted
            if batch:
                self._memory.upsert_chunks(batch)
                chunks_upserted += len(batch)
                batch.clear()

        missing: list[str] = []
        for rel in paths:
            target = self._resolve_path(rel)
            if not target.exists():
                missing.append(rel)
                continue
            if target.is_file():
                if self._index_file(workspace_id, target, batch, batch_size, flush):
                    files_indexed += 1
            elif target.is_dir():
                for file_path in sorted(target.rglob("*")):
                    if file_path.is_file() and is_text_file(str(file_path)):
                        if self._index_file(workspace_id, file_path, batch, batch_size, flush):
                            files_indexed += 1

        flush()
        if missing and files_indexed == 0 and chunks_upserted == 0:
            raise FileNotFoundError(
                f"No files indexed. Missing or empty paths under {self._workspace_root}: {missing}"
            )
        duration_ms = int((time.monotonic() - started) * 1000)
        return IndexResult(
            workspace_id=workspace_id,
            files_indexed=files_indexed,
            chunks_upserted=chunks_upserted,
            duration_ms=duration_ms,
        )

    def _resolve_path(self, rel: str) -> Path:
        root = self._workspace_root
        candidate = Path(rel)
        if candidate.is_absolute():
            return jail_under_root(root, candidate)
        return jail_under_root(root, root / rel)

    def _index_file(
        self,
        workspace_id: str,
        file_path: Path,
        batch: list[Chunk],
        batch_size: int,
        flush,
    ) -> bool:
        rel = str(file_path.relative_to(self._workspace_root))
        try:
            raw = file_path.read_bytes()
            text = raw.decode("utf-8", errors="ignore")
        except OSError:
            return False
        if self._blob_store is not None:
            blob_key = f"workspaces/{workspace_id}/{rel}"
            self._blob_store.put(blob_key, raw, content_type="text/plain")
        pieces = chunk_text(text)
        if not pieces:
            return False
        vectors = self._embedder.embed(pieces)
        for index, (piece, vector) in enumerate(zip(pieces, vectors, strict=True)):
            chunk_id = _make_chunk_id(workspace_id, rel, index)
            batch.append(
                Chunk(
                    chunk_id=chunk_id,
                    workspace_id=workspace_id,
                    path=rel,
                    text=piece,
                    embedding=vector,
                    metadata={"chunk_index": index},
                )
            )
            if len(batch) >= batch_size:
                flush()
        return True


def jail_under_root(root: Path, target: Path) -> Path:
    resolved = target.resolve()
    root = root.resolve()
    if not str(resolved).startswith(str(root)):
        raise PermissionError(f"Path outside workspace: {target}")
    return resolved


def _make_chunk_id(workspace_id: str, rel_path: str, index: int) -> str:
    raw = f"{workspace_id}:{rel_path}:{index}"
    return hashlib.sha256(raw.encode()).hexdigest()


async def index_workspace(
    workspace_id: str,
    paths: list[str],
    *,
    workspace_root: str | None = None,
) -> IndexResult:
    import asyncio

    from runtime.adapters.blob.minio_store import get_blob_store
    from runtime.config import Settings
    from runtime.intelligence.qdrant_memory import get_qdrant_memory

    settings = Settings()
    memory = get_qdrant_memory()
    if memory is None:
        raise RuntimeError("Semantic search unavailable (Qdrant disabled or down)")
    root = workspace_root or settings.workspace_root
    blob_store = get_blob_store()
    indexer = WorkspaceIndexer(memory, root, blob_store=blob_store)
    return await asyncio.to_thread(indexer.index, workspace_id, paths)
