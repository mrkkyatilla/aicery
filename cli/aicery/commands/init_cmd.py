from pathlib import Path

import typer
import yaml


def init_workspace(
    name: str = typer.Argument(
        ".",
        help="Workspace folder (use '.' for current directory).",
    ),
) -> None:
    root = Path(".").resolve() if name in (".", "./") else Path(name)
    root.mkdir(parents=True, exist_ok=True)
    key_dir = root / ".aicery"
    key_dir.mkdir(parents=True, exist_ok=True)
    key_file = key_dir / "api_key"
    if not key_file.exists():
        key_file.write_text("dev\n")
    key_file.chmod(0o600)

    config = {
        "runtime_url": "http://localhost:8000",
        "api_key_file": str(key_file.relative_to(root)),
        "default_agent": "research",
        "workspace_id": "local",
    }
    (root / "aicery.yaml").write_text(yaml.safe_dump(config, sort_keys=False))
    typer.echo(f"Created {root / 'aicery.yaml'}")
