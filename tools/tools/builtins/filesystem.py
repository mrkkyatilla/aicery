
from tools.registry import tool
from tools.sandbox.jail import jail_path

READ_FILE_SCHEMA = {
    "type": "object",
    "properties": {"path": {"type": "string"}},
    "required": ["path"],
}


@tool("read_file", READ_FILE_SCHEMA)
def read_file(path: str, *, workspace_root: str = ".") -> dict:
    target = jail_path(workspace_root, path)
    if not target.is_file():
        raise FileNotFoundError(str(target))
    return {"content": target.read_text(encoding="utf-8", errors="replace")}


@tool(
    "list_files",
    {
        "type": "object",
        "properties": {
            "path": {"type": "string"},
            "glob": {"type": "string"},
        },
    },
)
def list_files(path: str = ".", glob: str = "*", *, workspace_root: str = ".") -> dict:
    target = jail_path(workspace_root, path)
    if not target.is_dir():
        raise NotADirectoryError(str(target))
    files = [p.name for p in sorted(target.glob(glob)) if p.is_file()]
    return {"files": files, "path": str(target)}
