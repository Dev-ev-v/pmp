import time
from pathlib import Path

from pmp.player.events import MPVEventClient
from pmp.config import Config
from pmp.library.models import Song, Playlist
from pmp.player.ipc import MPVClient
from pmp.player.process import MPVProcess
from pmp.presentation.state import PlaybackState
from pmp.player.exceptions import MPVCommandError

class Player:

    def __init__(self, config: Config):

        self._config = config
        self._listeners = []
        
        self._events = MPVEventClient(
        	config
        )
        self._pending_end_events = []
        self._events_ready = False
        self._idle = None
        self._last_end_file_reason = None
        self._file_loaded_position = None

	        
        self._process = MPVProcess(
            config
        )

        self._client = MPVClient(
            config
        )
    		
        
    def ensure_ready(self):
    	self._process.start()
    	
    	if not self._events_ready:
    	   self._events.connect()
    	   self._events.observe_property("idle-active")
    	   self._events.observe_event("file-loaded")
    	   self._events.observe_event("end-file")
    	   self._events_ready = True
    
    def _wait_for_file_loaded(
    	self,
    	playlist_index: int,
    	timeout: float = 5,
    ):
    	deadline = time.monotonic() + timeout
    	while time.monotonic() < deadline:
    		self.process_events()
    		if self._file_loaded_position == playlist_index:
    			return
    		
    		time.sleep(0.01)
    		
    	raise RuntimeError(
    		f"Timeout esperando a música na posição {playlist_index}"
    	)
    
    def _wait_for_playlist_position(
    	self,
    	position: int,
    	timeout: float = 5,
    ):
    	
    	start = time.monotonic()
    	
    	while time.monotonic() - start < timeout:
    		current = self._get_property("playlist-pos")
    		if current == position:
    			return
    		
    		time.sleep(0.05)
    	
    	raise RuntimeError(
    		f"MPV não chegou à posição {position}"
    	)
    
    def wait_until_playing(self, timeout=5):
    	start = time.monotonic()
    	
    	while time.monotonic() - start < timeout:
    		idle = self._get_property("idle-active")
    		
    		if not idle:
    			return
    		
    		time.sleep(0.05)
    	
    	raise RuntimeError(
    		"Timeout esperando mpv iniciar a reprodução"
    	)
    
    def _seek_when_ready(
        self,
        position: float,
        timeout: float = 5,
    ):
        deadline = time.monotonic() + timeout

        while time.monotonic() < deadline:
            try:
                idle = self._get_property("idle-active")
                current_position = self._get_property("playlist-pos")
                duration = self._get_property("duration")

                if (
                    not idle
                    and current_position is not None
                    and duration is not None
                ):
                    self._client.command(
                        "seek",
                        position,
                        "absolute",
                    )
                    return

            except Exception:
                pass

            time.sleep(0.05)

        raise RuntimeError(
            f"Timeout esperando MPV ficar pronto para seek em {position}s"
        )
        
    def read_events(self):
    	return self._events.read_events()
    	
    def clear_end_file_reason(self):
    	self._last_end_file_reason = None
    	
    def _query_property(self, name):
    	return self._client.property(name)
    
    def _get_property(self, name):
        self.ensure_ready()
        return self._query_property(name)
   
        
    def append(self, song: Song):
    	self.ensure_ready()
    	
    	self._client.command(
    		"loadfile",
    		str(song.path),
    		"append",
    	)
    
    def play(
        self,
        songs: tuple[Song, ...],
        playlist_index: int = 0,
        time: float = 0,
    ):
        if not songs:
            return

        self.ensure_ready()
        self._file_loaded_position = None
        self._idle = False

        self._client.command(
            "loadfile",
            str(songs[0].path),
            "replace",
        )

        for song in songs[1:]:
            self._client.command(
                "loadfile",
                str(song.path),
                "append",
            )

        if playlist_index > 0:
            self._client.command(
                "playlist-play-index",
                playlist_index,
            )

        self._wait_for_file_loaded(playlist_index)
        self._wait_for_playlist_position(playlist_index)

        if time > 0:
            self._seek_when_ready(time)
	   
    
    def pause(self):

        self.ensure_ready()

        self._client.command(
            "cycle",
            "pause",
        )  
        
    def stop(self):

        self.ensure_ready()

        self._client.command(
            "stop",
        )
        
    def next(self):

        self.ensure_ready()

        try:
            self._client.command(
            	"playlist-next",
            )
        except Exception:
        	return
        
    def previous(self):

        self.ensure_ready()

        try:
            self._client.command(
            	"playlist-prev",
            )
        except Exception:
        	return
        

    def volume(
        self,
        value: int,
    ):
        value = max(0, min(100, value))
        self.ensure_ready()

        self._client.command(
            "set_property",
            "volume",
            value,
        )
        
    def speed(
    	self,
    	value: float,
    ):
        value = max(0.25, min(2.0, value))
        self.ensure_ready()
        
        self._client.command(
        	"set_property",
        	"speed",
        	value
        )
        
    
    def loop_current(self, enabled: bool):
        
        self.ensure_ready()
        
        self._client.command(
        	"set_property",
        	"loop-file",
        	"yes" if enabled else "no"
        )
    
    def increase_volume(self, value: int):
        
        current = int(self._get_property("volume"))
        self.volume(current + value)
        
    def increase_speed(self, value: float):
        
        current = float(self._get_property("speed"))
        self.speed(current + value)
        
    def process_events(self):
    	events = self._events.read_events()
    	
    	for event in events:
    		event_name = event.get("event")
    		
    		if event_name == "property-change":
    		    if event.get("name") == "idle-active":
    		    	self._idle = event.get("data")
    		    	
    		elif event_name == "file-loaded":
    			self._file_loaded_position = self._get_property("playlist-pos")
    			self._current_file_position = self._file_loaded_position
    		
    		elif event_name == "end-file":
    			self._last_end_file_reason = event.get("reason")
    			
    			self._pending_end_events.append({
                    **event,
                    "playlist_position": self._current_file_position,
                })
    
    def get_loop_enabled(self):
            return self._get_property("loop-file")
            
            
    def seek_absolute(self, offset: float):
    	self.ensure_ready()
    	
    	self._client.command(
    		"seek",
    		offset,
    		"absolute",
    	)
    	
    def seek_relative(self, offset: float):
    	self.ensure_ready()
    	
    	self._client.command(
    		"seek",
    		offset,
    		"relative",
    	)
    	
    def set_playlist_position(self, position: int):
    	self.ensure_ready()
    	
    	self._client.command(
    		"set_property",
    		"playlist-pos",
    		position,
    	)
    	
    def consume_end_file_events(self) -> list[dict]:
    	events = self._pending_end_events
    	self._pending_end_events = []
    	return events   	
    
    @property
    def connected(self) -> bool:
    	return self._process.running()
    	
    @property
    def playback_position(self) -> tuple[int, float]:
        try:
        	playlist_index = self._get_property("playlist-pos")
        except Exception:
        	playlist_index = None
        	
        try:
        	time_pos = self._get_property("time-pos")
        except Exception:
        	time_pos = None
   
        return (
        	playlist_index if playlist_index is not None else 0,
        	time_pos if time_pos is not None else 0,
        )
    	
    @property
    def duration(self) -> float | None:
        try:
            value = self._get_property("duration")
        except MPVCommandError:
            return None

        if value is None:
            return None

        try:
            return float(value)
        except (TypeError, ValueError):
            return None
    
    @property
    def is_paused(self) -> bool:
    	return self._get_property("pause") or False
    
    @property
    def idle(self) -> bool:
    	return self._idle
    
    @property
    def last_end_file_reason(self):
    	return self._last_end_file_reason
    	
    @property
    def event_socket(self):
    	self.ensure_ready()
    	return self._events.socket
    	
    @property
    def playlist_position(self):
        try:
        	return self._get_property("playlist-pos")
        except Exception:
        	return None
    
    def _get_property_or(
        self,
        name,
        default,
        *,
        ensure_ready=True,
    ):
        try:
            if ensure_ready:
                value = self._get_property(name)
            else:
                value = self._query_property(name)

        except RuntimeError as exc:
            if "property unavailable" in str(exc):
                return default
            raise

        return default if value is None else value
    
    def state(
        self,
        song,
        queue,
        loop,
        shuffle,
        global_shuffle,
        playlist,
    ) -> PlaybackState:
        self.ensure_ready()
        idle = self._query_property("idle-active")

        if idle:
            return PlaybackState(
                title=None,
                artist=None,
                album=None,
                playlist=None,
                position=0,
                duration=0,
                speed=self._get_property_or(
                    "speed", 1.0, ensure_ready=False
                ),
                volume=self._get_property_or(
                    "volume", 0, ensure_ready=False
                ),
                paused=False,
                queue=queue,
                path=None,
                loop=loop,
                shuffle=shuffle,
                global_shuffle=global_shuffle,
            )
            
        return PlaybackState(
    		title=song.title if song else None,
    		artist=song.artist if song else None,
    		album=song.album if song else None,
    		position=self._get_property_or("time-pos", 0, ensure_ready=False),
    		duration=song.duration,
    		speed=self._get_property_or("speed", 1.0, ensure_ready=False),
    		volume=self._get_property_or("volume", 0, ensure_ready=False),
    		paused=self._get_property_or("pause", False, ensure_ready=False),
    		queue=queue,
    		path=str(song.path) if song else None,
    		loop=loop,
    		shuffle=shuffle,
    		global_shuffle=global_shuffle,
    		playlist=playlist.name if playlist else None,
    		playlist_position=self._get_property_or("playlist-pos", 0),
    	)