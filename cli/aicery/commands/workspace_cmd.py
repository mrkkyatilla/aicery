from pathlib import Path

import httpx
import typer
from aicery_sdk import AiceryClient

workspace_app = typer.Typer(name="workspace", help="Workspace indexing and search.")


@workspace_app.command("index")
def index_workspace_cmd(
    paths: list[str] = typer.Argument(..., help="Paths under workspace root to index."),
    workspace_id: str = typer.Option("local", "--workspace-id", help="Workspace id in Qdrant."),
    config: Path = typer.Option(Path("aicery.yaml"), "--config", help="Path to aicery.yaml"),
) -> None:
    """Index text files into Qdrant for semantic search."""
    client = AiceryClient.from_config(config)
    try:
        result = client.index_workspace(workspace_id=workspace_id, paths=paths)
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            typer.echo(
                "Runtime API has no POST /v1/workspace/index (stale container or old code).\n"
                "From the repo root rebuild the API:\n"
                "  docker compose -f deploy/docker-compose.yml up -d --build --wait api qdrant\n"
                "Or: make up",
                err=True,
            )
            raise typer.Exit(1) from exc
        detail = exc.response.text[:300] if exc.response.text else str(exc)
        typer.echo(f"Index failed (HTTP {exc.response.status_code}): {detail}", err=True)
        raise typer.Exit(1) from exc
    typer.echo(
        f"Indexed workspace={result['workspace_id']} "
        f"files={result['files_indexed']} chunks={result['chunks_upserted']} "
        f"({result['duration_ms']}ms)"
    )
