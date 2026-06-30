from __future__ import annotations

import logging

from core.ports.semantic_memory import Chunk
from runtime.config import Settings
from runtime.intelligence.qdrant_memory import QdrantSemanticMemory, get_qdrant_memory

logger = logging.getLogger(__name__)


def chunks_to_hits(chunks: list[Chunk]) -> list[dict]:
    hits: list[dict] = []
    for chunk in chunks:
        line = int(chunk.metadata.get("chunk_index", 0)) + 1
        snippet = chunk.text[:200].replace("\n", " ")
        hit = {"file": chunk.path, "line": line, "text": snippet}
        for key in ("importance", "category", "document_id"):
            if key in chunk.metadata:
                hit[key] = chunk.metadata[key]
        hits.append(hit)
    return hits


class HybridRetriever:
    """Vector search with grep fallback (E7 F3)."""

    def __init__(
        self,
        memory: QdrantSemanticMemory | None,
        *,
        workspace_root: str,
    ) -> None:
        self._memory = memory
        self._workspace_root = workspace_root

    def search(self, workspace_id: str, query: str, *, top_k: int = 5) -> dict:
        from tools.builtins.search_workspace import search_workspace as grep_search

        vector_hits: list[dict] = []
        if self._memory is not None:
            try:
                chunks = self._memory.search(workspace_id, query, top_k=top_k)
                vector_hits = chunks_to_hits(chunks)
            except Exception:
                logger.warning("Qdrant search failed; grep fallback only", exc_info=True)

        if len(vector_hits) >= 3:
            return {"hits": vector_hits[:top_k], "source": "vector"}

        grep_result = grep_search(query, path=".", max_hits=top_k, workspace_root=self._workspace_root)
        grep_hits = grep_result.get("hits", [])

        merged = _merge_hits(vector_hits, grep_hits, top_k=top_k)
        source = "hybrid" if vector_hits else "grep"
        return {"hits": merged, "source": source}


def _merge_hits(vector_hits: list[dict], grep_hits: list[dict], *, top_k: int) -> list[dict]:
    seen: set[tuple[str, int]] = set()
    merged: list[dict] = []
    for hit in vector_hits + grep_hits:
        key = (hit.get("file", ""), int(hit.get("line", 0)))
        if key in seen:
            continue
        seen.add(key)
        merged.append(hit)
        if len(merged) >= top_k:
            break
    return merged


def hybrid_search(
    query: str,
    path: str = ".",
    max_hits: int = 50,
    *,
    workspace_root: str,
    workspace_id: str | None = None,
) -> dict:
    settings = Settings()
    wid = workspace_id or settings.default_workspace_id
    memory = get_qdrant_memory()
    retriever = HybridRetriever(memory, workspace_root=workspace_root)
    result = retriever.search(wid, query, top_k=max_hits)
    return {"hits": result["hits"]}
