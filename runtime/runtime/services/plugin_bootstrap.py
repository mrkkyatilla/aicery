from __future__ import annotations

from agents.plugin_paths import parse_plugin_paths, set_plugin_roots
from runtime.config import Settings
from tools.registry.plugin_loader import load_plugin_paths


def bootstrap_plugins(settings: Settings | None = None) -> None:
    settings = settings or Settings()
    roots = parse_plugin_paths(
        settings.plugin_paths,
        workspace_root=settings.workspace_root,
    )
    set_plugin_roots(roots)
    if roots:
        load_plugin_paths(roots)
