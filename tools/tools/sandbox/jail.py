from pathlib import Path


class PathTraversalError(Exception):
    error_code = "TOOL_PATH_TRAVERSAL"


def jail_path(workspace_root: str, user_path: str) -> Path:
    root = Path(workspace_root).resolve()
    target = (root / user_path).resolve()
    if not str(target).startswith(str(root)):
        raise PathTraversalError(f"Path escapes workspace: {user_path}")
    return target
