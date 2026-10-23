import typer

from pmp.container import container


app = typer.Typer()


@app.callback(invoke_without_command=True)
def volume(
    value: int = typer.Argument(...),
):
    	
    container.playback.set_volume(
        value
    )