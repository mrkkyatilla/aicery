import typer

from aicery import __version__
from aicery.commands.agent import agent_app
from aicery.commands.dev import dev_status
from aicery.commands.drift_cmd import drift_app
from aicery.commands.graph_cmd import graph_app
from aicery.commands.init_cmd import init_workspace
from aicery.commands.replay_cmd import replay_run
from aicery.commands.trace_cmd import trace_app
from aicery.commands.workspace_cmd import workspace_app

app = typer.Typer(name="aicery", invoke_without_command=True, no_args_is_help=True)
app.command("init")(init_workspace)
app.add_typer(agent_app, name="agent")
app.add_typer(trace_app, name="trace")
app.command("replay", help="Replay a previous run with frozen mocks.")(replay_run)
app.add_typer(drift_app, name="drift")
app.add_typer(graph_app, name="graph")
app.add_typer(workspace_app, name="workspace")
app.command("dev")(dev_status)


@app.callback()
def main(
    version: bool = typer.Option(False, "--version", "-V", help="Show version and exit."),
) -> None:
    """Aicery CLI — agent runtime developer tools."""
    if version:
        typer.echo(__version__)
        raise typer.Exit()


if __name__ == "__main__":
    app()
