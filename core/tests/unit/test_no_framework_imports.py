import ast
from pathlib import Path

FORBIDDEN = frozenset({"fastapi", "langgraph", "redis", "sqlalchemy", "uvicorn"})

CORE_SRC = Path(__file__).resolve().parents[2] / "core"


def test_core_tree_has_no_framework_imports() -> None:
    violations: list[str] = []
    for path in CORE_SRC.rglob("*.py"):
        tree = ast.parse(path.read_text(), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    root = alias.name.split(".")[0]
                    if root in FORBIDDEN:
                        violations.append(f"{path}:{root}")
            elif isinstance(node, ast.ImportFrom) and node.module:
                root = node.module.split(".")[0]
                if root in FORBIDDEN:
                    violations.append(f"{path}:{root}")
    assert violations == [], f"Forbidden imports in core: {violations}"
