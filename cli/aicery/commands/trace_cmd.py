import json
from pathlib import Path

import typer
from aicery_sdk import AiceryClient

from core.domain.trace import TraceStep
from runtime.services.trace_miner import analyze_steps, load_report_schema

trace_app = typer.Typer(name="trace", invoke_without_command=True)


def _resolve_run_id(client: AiceryClient, run_id: str | None) -> str:
    if run_id and run_id != "last":
        return run_id
    last_file = Path(".aicery/last_run_id")
    if not last_file.is_file():
        raise typer.BadParameter("No last run — run an agent first or pass run_id")
    return last_file.read_text().strip()


@trace_app.callback()
def trace_run(
    ctx: typer.Context,
    run_id: str = typer.Argument("last", help="Run id or 'last'."),
    config: Path = typer.Option(Path("aicery.yaml"), "--config", help="Path to aicery.yaml"),
) -> None:
    """Show ASCII timeline for a run trace (default when no subcommand)."""
    if ctx.invoked_subcommand is not None:
        return
    client = AiceryClient.from_config(config)
    rid = _resolve_run_id(client, run_id)
    body = client.get_trace(rid)
    steps = body.get("steps", [])
    if not steps:
        typer.echo(f"No trace steps for run {rid}")
        raise typer.Exit(1)
    typer.echo(f"Trace: {rid} ({len(steps)} steps)")
    typer.echo("-" * 60)
    for step in steps:
        dur = step.get("duration_ms")
        dur_s = f"{dur}ms" if dur is not None else "—"
        typer.echo(
            f"  [{step['type']:6}] {step['name']:24} {step['status']:7} {dur_s}"
        )
    typer.echo("-" * 60)


@trace_app.command("analyze")
def trace_analyze(
    agent: str = typer.Option("research", "--agent", help="Agent id label for report."),
    min_runs: int = typer.Option(10, "--min-runs", help="Minimum runs before high-confidence stats."),
    fixture: Path | None = typer.Option(
        None,
        "--fixture",
        help="Optional fixture JSON with steps array.",
    ),
) -> None:
    """Read-only trace analytics: node visits, dead steps, avg tokens."""
    path = fixture or Path("runtime/data/trace_miner/fixture_steps.json")
    if not path.is_file():
        typer.echo(f"Fixture not found: {path}", err=True)
        raise typer.Exit(1)
    raw = json.loads(path.read_text(encoding="utf-8"))
    steps = [TraceStep.model_validate(item) for item in raw.get("steps", [])]
    report = analyze_steps(
        steps,
        agent_id=raw.get("agent_id", agent),
        min_runs=min_runs,
        known_nodes=raw.get("known_nodes"),
    )
    typer.echo(json.dumps(report.to_dict(), indent=2))
    _ = load_report_schema()
