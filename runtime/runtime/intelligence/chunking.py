from __future__ import annotations

TEXT_SUFFIXES = {
    ".md",
    ".txt",
    ".py",
    ".yaml",
    ".yml",
    ".json",
    ".rst",
    ".toml",
    ".sh",
}


def is_text_file(path: str) -> bool:
    from pathlib import Path

    suffix = Path(path).suffix.lower()
    return suffix in TEXT_SUFFIXES or suffix == ""


def chunk_text(text: str, *, size: int = 2048, overlap: int = 256) -> list[str]:
    """Character windows (~512 tokens at size 2048)."""
    if not text:
        return []
    if len(text) <= size:
        return [text]
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(len(text), start + size)
        chunks.append(text[start:end])
        if end >= len(text):
            break
        start = max(0, end - overlap)
    return chunks
