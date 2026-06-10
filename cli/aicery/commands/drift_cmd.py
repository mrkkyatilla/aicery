from pathlib import Path

import typer

from runtime.services.drift_evaluator import evaluate_drift, format_report

drift_app = typer.Typer(name="drift", help="Trace-backed drift evaluation (soft report).")


@drift_app.command("check")
def drift_check(
    baseline: Path = typer.Option(
        Path("runtime/data/drift/golden_runs.json"),
        "--baseline",
        help="Golden runs JSON baseline.",
    ),
) -> None:
    """Compare golden runs against mock replay output; soft report (exit 0)."""
    report = evaluate_drift(baseline=baseline)
    typer.echo(format_report(report))
    raise typer.Exit(0)
