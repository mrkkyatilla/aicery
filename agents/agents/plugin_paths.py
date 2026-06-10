from __future__ import annotations

from pathlib import Path

_PLUGIN_ROOTS: list[Path] = []


def set_plugin_roots(paths: list[Path]) -> None:
    global _PLUGIN_ROOTS
    _PLUGIN_ROOTS = [p.resolve() for p in paths if p.is_dir()]
    from agents.manifest import load_manifest

    load_manifest.cache_clear()


def get_plugin_roots() -> list[Path]:
    return list(_PLUGIN_ROOTS)


def parse_plugin_paths(raw: str, *, workspace_root: str = ".") -> list[Path]:
    if not raw or not raw.strip():
        return []
    root = Path(workspace_root).resolve()
    paths: list[Path] = []
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        candidate = Path(part)
        if not candidate.is_absolute():
            candidate = root / candidate
        resolved = candidate.resolve()
        if not resolved.is_dir():
            raise ValueError(f"PLUGIN_PATHS entry is not a directory: {part}")
        paths.append(resolved)
    return paths
