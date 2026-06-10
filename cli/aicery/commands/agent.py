import time
from pathlib import Path

import typer
from aicery_sdk import AiceryClient

agent_app = typer.Typer(help="Run agents against the runtime.")


@agent_app.command("run")
def agent_run(
    agent: str = typer.Argument(..., help="Agent id (echo, research, …)."),
    input: str = typer.Option(..., "--input", "-i", help="Run input text."),
    config: Path = typer.Option(Path("aicery.yaml"), "--config", help="aicery.yaml path."),
    stream: bool = typer.Option(True, "--stream/--no-stream", help="Stream SSE tokens."),
    workspace_id: str | None = typer.Option(None, "--workspace-id"),
) -> None:
    client = AiceryClient.from_config(config)
    run = client.create_run(agent_id=agent, input=input, workspace_id=workspace_id)
    client.save_last_run_id(run.id)
    if stream:
        for event in client.stream_run(run.id):
            if event.event == "token":
                typer.echo(event.data.get("text", ""), nl=False)
            elif event.event == "error":
                typer.echo(
                    f"\n[error] {event.data.get('error_code')}: {event.data.get('message')}",
                    err=True,
                )
                raise typer.Exit(1)
            elif event.event == "done":
                typer.echo()
                final = client.get_run(run.id)
                raise typer.Exit(0 if final.status == "completed" else 1)
    else:
        for _ in range(60):
            final = client.get_run(run.id)
            if final.status in ("completed", "failed", "cancelled"):
                typer.echo(final.output_text or "")
                raise typer.Exit(0 if final.status == "completed" else 1)
            time.sleep(0.2)
    raise typer.Exit(1)
