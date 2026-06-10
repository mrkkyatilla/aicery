import time
from pathlib import Path

import typer
from aicery_sdk import AiceryClient


def _last_run_id() -> str:
    last_file = Path(".aicery/last_run_id")
    if not last_file.is_file():
        raise typer.BadParameter("No last run — run an agent first")
    return last_file.read_text().strip()


def replay_run(
    run_id: str = typer.Argument("last", help="Source run id or 'last'."),
    mock_tools: bool = typer.Option(True, "--mock-tools/--no-mock-tools"),
    input: str | None = typer.Option(None, "--input", "-i", help="Override input (must match source)."),
    config: Path = typer.Option(Path("aicery.yaml"), "--config", help="Path to aicery.yaml"),
) -> None:
    """Replay a run using trace-backed mock provider/tools."""
    client = AiceryClient.from_config(config)
    source_id = run_id if run_id != "last" else _last_run_id()
    source = client.get_run(source_id)
    run_input = input if input is not None else source.input_text or ""
    if not run_input:
        raise typer.BadParameter("Could not determine input text for replay")

    run = client.create_run(
        agent_id=source.agent_id,
        input=run_input,
        execute=True,
        replay_source_run_id=source_id,
        mock_tools=mock_tools,
    )
    client.save_last_run_id(run.id)

    for _ in range(120):
        final = client.get_run(run.id)
        if final.status in ("completed", "failed", "cancelled"):
            typer.echo(final.output_text or "")
            raise typer.Exit(0 if final.status == "completed" else 1)
        time.sleep(0.25)
    raise typer.Exit(1)
