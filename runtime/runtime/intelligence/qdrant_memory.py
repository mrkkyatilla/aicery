from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Any

from core.ports.semantic_memory import Chunk
from runtime.config import Settings

logger = logging.getLogger(__name__)


class QdrantSemanticMemory:
    """SemanticMemoryPort backed by Qdrant collection workspace_chunks."""

    def __init__(self, url: str, collection: str, vector_size: int) -> None:
        self._url = url
        self._collection = collection
        self._vector_size = vector_size
        self._client: Any = None

    def _get_client(self):
        if self._client is None:
            from qdrant_client import QdrantClient

            self._client = QdrantClient(url=self._url, timeout=5)
            self._ensure_collection()
        return self._client

    def _ensure_collection(self) -> None:
        from qdrant_client.models import Distance, VectorParams

        client = self._client
        names = {c.name for c in client.get_collections().collections}
        if self._collection not in names:
            client.create_collection(
                collection_name=self._collection,
                vectors_config=VectorParams(size=self._vector_size, distance=Distance.COSINE),
            )

    def upsert_chunks(self, chunks: list[Chunk]) -> None:
        if not chunks:
            return
        from qdrant_client.models import PointStruct

        client = self._get_client()
        points = []
        for chunk in chunks:
            if not chunk.embedding:
                continue
            points.append(
                PointStruct(
                    id=_chunk_point_id(chunk.chunk_id),
                    vector=chunk.embedding,
                    payload={
                        "chunk_id": chunk.chunk_id,
                        "workspace_id": chunk.workspace_id,
                        "path": chunk.path,
                        "text": chunk.text,
                        **chunk.metadata,
                    },
                )
            )
        if points:
            client.upsert(collection_name=self._collection, points=points)

    def search(self, workspace_id: str, query: str, top_k: int = 5) -> list[Chunk]:
        from qdrant_client.models import FieldCondition, Filter, MatchValue

        client = self._get_client()
        embedder = None
        from runtime.intelligence.embeddings import get_embedder

        embedder = get_embedder()
        vector = embedder.embed([query])[0]
        results = client.search(
            collection_name=self._collection,
            query_vector=vector,
            limit=top_k,
            query_filter=Filter(
                must=[FieldCondition(key="workspace_id", match=MatchValue(value=workspace_id))]
            ),
        )
        chunks: list[Chunk] = []
        for hit in results:
            payload = hit.payload or {}
            chunks.append(
                Chunk(
                    chunk_id=str(payload.get("chunk_id", hit.id)),
                    workspace_id=str(payload.get("workspace_id", workspace_id)),
                    path=str(payload.get("path", "")),
                    text=str(payload.get("text", "")),
                    metadata={k: v for k, v in payload.items() if k not in ("chunk_id", "workspace_id", "path", "text")},
                )
            )
        return chunks

    async def upsert_chunks_async(self, chunks: list[Chunk]) -> None:
        await asyncio.to_thread(self.upsert_chunks, chunks)

    async def search_async(self, workspace_id: str, query: str, top_k: int = 5) -> list[Chunk]:
        return await asyncio.to_thread(self.search, workspace_id, query, top_k)


def _chunk_point_id(chunk_id: str) -> str:
    """Stable UUID from chunk_id for idempotent upsert."""
    return str(uuid.uuid5(uuid.NAMESPACE_URL, chunk_id))


def get_qdrant_memory() -> QdrantSemanticMemory | None:
    settings = Settings()
    if not settings.semantic_search_enabled:
        return None
    try:
        return QdrantSemanticMemory(
            url=settings.qdrant_url,
            collection=settings.qdrant_collection,
            vector_size=settings.embedding_dimensions,
        )
    except Exception:
        logger.warning("Qdrant unavailable; semantic search disabled")
        return None
