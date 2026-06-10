from __future__ import annotations

import importlib.util
import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

_LOADED: set[str] = set()


def _load_module_from_path(path: Path, module_name: str) -> None:
    if module_name in _LOADED:
        return
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load plugin module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    _LOADED.add(module_name)
    logger.info("Loaded plugin module %s from %s", module_name, path)


def load_showcase(root: Path) -> None:
    """Load tools/*.py and agents/graph.py from a showcase package root."""
    root = root.resolve()
    if not root.is_dir():
        raise ValueError(f"Showcase root is not a directory: {root}")

    tools_dir = root / "tools"
    if tools_dir.is_dir():
        tools_dir_str = str(tools_dir)
        inserted = tools_dir_str not in sys.path
        if inserted:
            sys.path.insert(0, tools_dir_str)
        try:
            for py in sorted(tools_dir.glob("*.py")):
                if py.name.startswith("_"):
                    continue
                mod_name = f"aicery_showcase_{root.name}_{py.stem}"
                _load_module_from_path(py, mod_name)
        finally:
            if inserted:
                sys.path.remove(tools_dir_str)

    graph_py = root / "agents" / "graph.py"
    if graph_py.is_file():
        mod_name = f"aicery_showcase_{root.name}_graph"
        _load_module_from_path(graph_py, mod_name)


def load_plugin_paths(paths: list[Path]) -> None:
    for root in paths:
        load_showcase(root)


def reset_loaded_modules() -> None:
    _LOADED.clear()
