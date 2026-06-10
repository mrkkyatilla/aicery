from __future__ import annotations

import re
import subprocess
from pathlib import Path

from tools.registry import tool
from tools.sandbox.jail import jail_path

_SEMANTIC_BACKEND = None


def register_semantic_backend(fn) -> None:
    """Runtime registers hybrid_search at startup (E7)."""
    global _SEMANTIC_BACKEND
    _SEMANTIC_BACKEND = fn


SEARCH_SCHEMA = {
    "type": "object",
    "properties": {
        "query": {"type": "string"},
        "path": {"type": "string"},
        "max_hits": {"type": "integer"},
    },
    "required": ["query"],
}


def _grep_fallback(root: Path, query: str, max_hits: int) -> list[dict]:
    pattern = re.compile(re.escape(query), re.IGNORECASE)
    hits: list[dict] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if path.suffix in {".pyc", ".png", ".jpg", ".woff", ".bin"}:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for line_no, line in enumerate(text.splitlines(), start=1):
            if pattern.search(line):
                hits.append(
                    {
                        "file": str(path.relative_to(root)),
                        "line": line_no,
                        "text": line[:200],
                    }
                )
                if len(hits) >= max_hits:
                    return hits
    return hits


@tool("search_workspace", SEARCH_SCHEMA)
def search_workspace(
    query: str,
    path: str = ".",
    max_hits: int = 50,
    *,
    workspace_root: str = ".",
) -> dict:
    if _SEMANTIC_BACKEND is not None:
        try:
            return _SEMANTIC_BACKEND(
                query,
                path=path,
                max_hits=max_hits,
                workspace_root=workspace_root,
            )
        except Exception:
            pass
    root = jail_path(workspace_root, path)
    if not root.is_dir():
        raise NotADirectoryError(str(root))

    try:
        proc = subprocess.run(
            [
                "rg",
                "-n",
                "--max-count",
                str(max_hits),
                "--glob",
                "!**/.git/**",
                query,
                str(root),
            ],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return {"hits": _grep_fallback(root, query, max_hits)}

    hits: list[dict] = []
    for line in proc.stdout.splitlines():
        if len(hits) >= max_hits:
            break
        parts = line.split(":", 2)
        if len(parts) < 3:
            continue
        file_path, line_no, text = parts[0], parts[1], parts[2]
        try:
            rel = Path(file_path).relative_to(root)
        except ValueError:
            rel = Path(file_path).name
        hits.append({"file": str(rel), "line": int(line_no), "text": text[:200]})
    if not hits and proc.returncode != 0:
        return {"hits": _grep_fallback(root, query, max_hits)}
    return {"hits": hits}
