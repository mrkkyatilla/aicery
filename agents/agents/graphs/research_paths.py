from __future__ import annotations

import re

from core.ports.tool_executor import ToolExecutorPort

_PATH_RE = re.compile(r"[\w./-]+\.(?:md|txt|rst)\b", re.IGNORECASE)


def extract_path(text: str) -> str | None:
    """Pick the most specific workspace-relative file path from user text."""
    candidates: list[str] = []
    for match in _PATH_RE.finditer(text):
        candidates.append(match.group(0).strip("'\""))
    read_match = re.search(r"(?:read|file|path)[:\s]+([^\s]+)", text, re.IGNORECASE)
    if read_match:
        candidates.append(read_match.group(1).strip("'\""))
    if not candidates:
        return None
    return max(candidates, key=len)


async def resolve_research_file_path(
    user_text: str,
    tools: ToolExecutorPort,
    *,
    run_id: str,
    agent_id: str,
) -> str:
    """Prefer explicit path; else top hit from search_workspace (E7 semantic or grep)."""
    path = extract_path(user_text)
    if path and "/" in path and len(path) > 12:
        return path
    try:
        outcome = await tools.invoke(
            "search_workspace",
            {"query": user_text, "max_hits": 5},
            run_id=run_id,
            agent_id=agent_id,
        )
        hits = outcome["result"].get("hits", [])
        if hits:
            return str(hits[0]["file"])
    except Exception:
        pass
    return path or "README.md"
