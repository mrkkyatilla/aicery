import typer

from agents.graph_export import list_graph_keys, render_all_graphs, render_graph

graph_app = typer.Typer(help="Show agent / pipeline graphs (ASCII or Mermaid).")


@graph_app.callback(invoke_without_command=True)
def graph_show(
    ctx: typer.Context,
    name: str = typer.Argument(
        None,
        help="Agent or pipeline id (echo, research, research-chain). Omit to list all.",
    ),
    format: str = typer.Option(
        "ascii",
        "--format",
        "-f",
        help="Output format: ascii or mermaid.",
    ),
) -> None:
    """Export LangGraph topology (from built-in specs)."""
    if ctx.invoked_subcommand is not None:
        return
    fmt = format.lower().strip()
    if fmt not in ("ascii", "mermaid"):
        typer.echo(f"Unknown format: {format} (use ascii or mermaid)", err=True)
        raise typer.Exit(1) from None
    if name is None:
        typer.echo(render_all_graphs(format=fmt))
        typer.echo("")
        typer.echo(f"Available: {', '.join(list_graph_keys())}")
        return
    try:
        typer.echo(render_graph(name, format=fmt))
    except KeyError:
        typer.echo(f"Unknown graph: {name}", err=True)
        typer.echo(f"Available: {', '.join(list_graph_keys())}", err=True)
        raise typer.Exit(1) from None
