import subprocess

import typer


def dev_status() -> None:
    typer.echo("Runtime: http://localhost:8000")
    typer.echo("Start stack: make up")
    typer.echo("Tail API logs: make logs")
    result = subprocess.run(
        ["curl", "-sf", "http://localhost:8000/health"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode == 0:
        typer.echo(f"Health: {result.stdout.strip()}")
    else:
        typer.echo("Health: API not reachable (run make up)")
