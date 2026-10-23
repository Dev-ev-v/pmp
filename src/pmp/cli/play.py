import typer

from pmp.container import container
from pmp.cli.play_resolver import PlayResolver
from pmp.ipc.client import IPCClient
from pmp.daemon.daemon_manager import DaemonManager
from pmp.paths import paths


app = typer.Typer()

daemon_manager = DaemonManager(container.config)


@app.callback(invoke_without_command=True)
def play(
    name: str = typer.Argument(None),
    shuffle: bool = typer.Option(None, "--shuffle", "-s"),
    global_shuffle: bool = typer.Option(
        None,
        "--global_shuffle",
        "-gs",
    ),
):
    if not container.library.music_dir_exists:
        print("Music dir not defined in config file")
        print(f"To continue, use the path of your music dir in {paths.config}")
        return
        
    resolver = PlayResolver(
        container.search,
        container.selector,
    )

    target = None
    can_resume = None

    if name:
        selected = resolver.resolve(name)
        target = resolver.serialize(selected)
        
    queue = container.playback.get_queue_songs()
    if queue:
    	can_resume = container.selector.confirm("An existing queue was found, would you like to resume it?")

    daemon_manager.ensure_running()

    client = IPCClient()

    try:
        response = client.send(
        	"play",
        	{
        		"target": target,
        		"shuffle": shuffle,
        		"global_shuffle": global_shuffle,
        		"resume": can_resume,
        	},
        )
        if response != "ok":
        	print("Response:", response)
    except ConnectionError as exc:
    	print(f"Communication error: {exc}")
    	raise