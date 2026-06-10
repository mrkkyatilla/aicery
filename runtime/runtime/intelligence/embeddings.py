from __future__ import annotations

import hashlib
import math
from typing import Protocol

from core.domain.provider_policy import ModelRef
from runtime.config import Settings


class EmbedderPort(Protocol):
    @property
    def dimensions(self) -> int: ...

    def embed(self, texts: list[str]) -> list[list[float]]: ...


class HashEmbedder:
    """Deterministic fallback when provider key missing (dev/tests)."""

    def __init__(self, dimensions: int = 768) -> None:
        self._dimensions = dimensions

    @property
    def dimensions(self) -> int:
        return self._dimensions

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [_hash_vector(t, self._dimensions) for t in texts]


class GeminiEmbedder:
    def __init__(self, api_key: str, model: str = "gemini-embedding-001", dimensions: int = 768) -> None:
        self._api_key = api_key
        self._model = model
        self._dimensions = dimensions

    @property
    def dimensions(self) -> int:
        return self._dimensions

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=self._api_key)
        config = types.EmbedContentConfig(output_dimensionality=self._dimensions)
        response = client.models.embed_content(
            model=self._model, contents=texts, config=config
        )
        vectors: list[list[float]] = []
        for emb in response.embeddings:
            values = getattr(emb, "values", None) or emb.get("values", [])  # type: ignore[union-attr]
            vectors.append(list(values))
        return vectors


def _hash_vector(text: str, dimensions: int) -> list[float]:
    digest = hashlib.sha256(text.encode()).digest()
    raw = [digest[i % len(digest)] / 255.0 for i in range(dimensions)]
    norm = math.sqrt(sum(v * v for v in raw)) or 1.0
    return [v / norm for v in raw]


def get_embedder(ref: ModelRef | None = None) -> EmbedderPort:
    settings = Settings()
    if ref is None:
        if settings.gemini_api_key and not settings.use_mock_provider:
            return GeminiEmbedder(
                settings.gemini_api_key,
                model=settings.embedding_model,
                dimensions=settings.embedding_dimensions,
            )
        return HashEmbedder(dimensions=settings.embedding_dimensions)
    if ref.provider == "mock":
        return HashEmbedder(dimensions=settings.embedding_dimensions)
    if ref.provider == "openai":
        # OpenAI embeddings optional in CP-1; fall back to gemini or hash
        if settings.gemini_api_key and not settings.use_mock_provider:
            return GeminiEmbedder(
                settings.gemini_api_key,
                model=settings.embedding_model,
                dimensions=settings.embedding_dimensions,
            )
        return HashEmbedder(dimensions=settings.embedding_dimensions)
    if ref.provider == "gemini":
        if settings.gemini_api_key and not settings.use_mock_provider:
            return GeminiEmbedder(
                settings.gemini_api_key,
                model=ref.model or settings.embedding_model,
                dimensions=settings.embedding_dimensions,
            )
        return HashEmbedder(dimensions=settings.embedding_dimensions)
    raise ValueError(f"Unknown embedding provider: {ref.provider}")
