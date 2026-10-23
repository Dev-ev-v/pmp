import typer

from pmp.container import container

app = typer.Typer()


@app.callback(invoke_without_command=True)
def stats():
	
	stats = container.playback.get_stats()
	get_song_by_path = container.library.get_song_by_path
	container.presenter.show_stats(stats, get_song_by_path)