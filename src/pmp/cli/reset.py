import typer

from pmp.daemon.daemon_manager import DaemonManager
from pmp.container import container

app = typer.Typer()

@app.callback(invoke_without_command=True)
def reset(
    yes: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Skip confirmation.",
    ),
):
    """Recover the PMP playback processes after a failure."""

    if not yes and not typer.confirm(
        "Terminate the PMP daemon and its mpv process?"
    ):
        raise typer.Abort()

    try:
        DaemonManager(container.config).reset()
    except (OSError, RuntimeError) as exc:
        typer.echo(f"Reset failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    typer.echo("PMP recovery completed.")
