import typer
import time
import sys
import time
import termios
import tty
import select
import subprocess
import json

from pmp.presentation.state import PlaybackState
from pmp.container import container
from pmp.player.exceptions import MPVCommandError
from pmp.cli.watch_controller import WatchController
from pmp.daemon.daemon_manager import DaemonManager
from pmp.ipc.client import IPCClient

daemon_manager = DaemonManager(container.config)
client = IPCClient()

app = typer.Typer()

@app.command()
def pause():
    daemon_manager.ensure_running()

    response = client.send("pause")

    if response != "ok":
        print(response)
    

@app.command()
def stop():

    daemon_manager.ensure_running()

    response = client.send("stop")

    if response != "ok":
        print(response)
    
    
@app.command()
def next():
	daemon_manager.ensure_running()
	
	response = client.send("next")
	
	if response != "ok":
	   print(response)
    
       
@app.command()
def previous():

    daemon_manager.ensure_running()

    response = client.send("previous")
    
    if response != "ok":
    	print(response)
    

@app.command()
def status():
    try:
        data = client.send("get_state")
        state = PlaybackState(**data)
    except (RuntimeError, ConnectionError, json.JSONDecodeError, TypeError, ValueError) as e:
        print(f"Unable to retrieve playback state: {e}")
        return

    container.presenter.show_state(state)
	
	
def read_key():
    key = sys.stdin.read(1)

    if key != "\x1b":
        return key

    if sys.stdin.read(1) != "[":
        return None

    arrow = sys.stdin.read(1)

    return {
        "A": "UP",
        "B": "DOWN",
        "C": "RIGHT",
        "D": "LEFT",
    }.get(arrow)

@app.command()
def watch():
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)

    controller = WatchController(container.playback)

    was_idle = container.player.idle
    last_render = 0.0
    render_interval = 0.2

    try:
        tty.setcbreak(fd)

        while controller.running:
            ready, _, _ = select.select(
                [sys.stdin],
                [],
                [],
                0.05,
            )
            if sys.stdin in ready:
            	key = read_key()
            	if key is not None:
            		controller.execute(key)

            now = time.monotonic()

            if now - last_render < render_interval:
                continue

            last_render = now

            print("\033[H\033[J", end="")

            idle = container.player.idle
            reason = container.player.last_end_file_reason
            
            if idle and not was_idle and reason == "eof":
                container.player.clear_end_file_reason()
                continue

            was_idle = idle

            controls = container.renderer.render_controls(controller.bindings)
            status()
            print()
            print(controls)

    finally:
        termios.tcsetattr(
            fd,
            termios.TCSADRAIN,
            old_settings,
        )

@app.command()  
def queue():
	
	queue = container.playback.get_queue_songs()	   
	playlist_index = container.player.playback_position[0]
	container.presenter.show_queue(queue, playlist_index)
	
@app.command()
def library():
	playlists = container.library.playlists
	container.presenter.show_library(playlists, container.library.scan_errors)	

@app.command()
def shuffle():
	shuffle = container.playback.shuffle()
	print("shuffle:", shuffle)                                              
@app.command()
def global_shuffle():
	gs = container.playback.global_shuffle()
	print("global_shuffle:", gs) 	            	                                                 	
			
@app.command()
def loop():
	loop = container.playback.loop()
	print("loop:", loop)                                                          	                                                 