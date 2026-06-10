from typing import Protocol

from pydantic import BaseModel, Field


class Chunk(BaseModel):
    chunk_id: str
    workspace_id: str
    path: str
    text: str
    embedding: list[float] | None = None
    metadata: dict = Field(default_factory=dict)


class SemanticMemoryPort(Protocol):
    """Vector / semantic workspace memory (E7 implements)."""

    async def upsert_chunks(self, chunks: list[Chunk]) -> None: ...

    async def search(
        self, workspace_id: str, query: str, top_k: int = 5
    ) -> list[Chunk]: ...
