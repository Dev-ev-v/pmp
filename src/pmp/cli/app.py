import typer

from pmp.cli.play import app as play_app
from pmp.cli.volume import app as volume_app
from pmp.cli.stats import app as stats_app
from pmp.cli.reset import app as reset_app
from pmp.cli.playback import (
    pause,
    stop,
    next,
    previous,
    status,
    watch,
    queue,
    library,
    loop,
    shuffle,
    global_shuffle,
)


app = typer.Typer()

app.add_typer(
    play_app,
    name="play",
)

app.add_typer(
	volume_app,
	name="volume",
)

app.add_typer(
	stats_app,
	name="stats",
)

app.add_typer(
	reset_app,
	name="reset",
)

app.command()(pause)
app.command()(stop)
app.command()(next)
app.command()(previous)
app.command()(status)
app.command()(watch)
app.command()(queue)
app.command()(library)
app.command()(loop)
app.command()(shuffle)
app.command()(global_shuffle)