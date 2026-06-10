from __future__ import annotations

import math

from core.ports.semantic_memory import Chunk
from runtime.intelligence.embeddings import HashEmbedder


class InMemorySemanticMemory:
    """Test/dev memory: stores chunks and does cosine search (HashEmbedder-friendly)."""

    def __init__(self, vector_size: int = 768) -> None:
        self._chunks: list[Chunk] = []
        self._vector_size = vector_size
        self._embedder = HashEmbedder(dimensions=vector_size)

    def upsert_chunks(self, chunks: list[Chunk]) -> None:
        by_id = {c.chunk_id: c for c in self._chunks}
        for chunk in chunks:
            by_id[chunk.chunk_id] = chunk
        self._chunks = list(by_id.values())

    def search(self, workspace_id: str, query: str, top_k: int = 5) -> list[Chunk]:
        if not self._chunks:
            return []
        qvec = self._embedder.embed([query])[0]
        scored: list[tuple[float, Chunk]] = []
        for chunk in self._chunks:
            if chunk.workspace_id != workspace_id or not chunk.embedding:
                continue
            scored.append((_cosine(qvec, chunk.embedding), chunk))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [c for _, c in scored[:top_k]]


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(x * x for x in b)) or 1.0
    return dot / (na * nb)
