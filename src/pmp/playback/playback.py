import random
from pathlib import Path

from pmp.library.library import MusicLibrary
from pmp.library.models import Song, Playlist
from pmp.player.player import Player
from pmp.presentation.state import PlaybackState

from pmp.storage.session import PlaybackSession
from pmp.storage.config import UserConfig
from pmp.storage.stats import Stats

from pmp.player.exceptions import MPVCommandError

from pmp.services.exceptions import (
    SongNotFoundError,
    PlaylistNotFoundError,
    MultipleResultsError,
)

QUEUE_SIZE = 3
PLAY_THRESHOLD = 30.0
LIMIT_VOLUME = 100

class PlaybackService:

    def __init__(
    	self,
    	library,
    	player,
    	search,
    	session_store,
    	config_store,
    	stats_store,
    	STATS_SAMPLE_INTERVAL,
	):

        self._library = library
        self._player = player
        self._search = search
        self._session_store = session_store
        self._config_store = config_store
        self._stats_store = stats_store
        
        self._session = self._session_store.load()
        self._config = self._config_store.load()
        self._stats = self._stats_store.load()
        self.set_volume(self._config.volume)
        self._save_config()
        
        self._cycle = []
        self._cycle_used = set()
        
        self._tracked_song_path = None
        self._current_track_listened_seconds = 0.0
        self._current_track_play_counted = False
        self._current_track_duration = None
        
        self.STATS_SAMPLE_INTERVAL = STATS_SAMPLE_INTERVAL
        self._last_sample_position = None
        self._last_sample_path = None
        		
    ######
    ##OTHERS##
    ######
    
    def ensure_ready(self):
        self._player.ensure_ready()
        
    def is_playing(self) -> bool:
    	return not self._player.idle and not self._player.is_paused
    
    def get_queue_songs(self) -> PlaybackSession or None:
    	session = self._session_store.load()
    	
    	if session is None:
    		return []
    	
    	queue = [
    		self._library.get_song_by_path(path)
    		for path in session.queue
    	]
    	
    	return queue
    
    def refresh_session(self):
    	queue = self.get_queue_songs()
    	pos, time = self._player.playback_position
    	self._update_session(
        	queue=queue,
        	pos=pos,
        	time=time,
        )
    	    
    def save_session(self):
    	self._session_store.save(self._session)
    
    def _update_session(
    	self,
    	queue: tuple[Song, ...],
    	pos: int,
    	time: float,
    ):
        self._session = PlaybackSession(
        	queue=[song.path for song in queue],
        	pos=pos,
        	time=time,
        )
        
    def _save_config(self):        
        config = UserConfig(
        	shuffle=self._config.shuffle,
        	global_shuffle=self._config.global_shuffle,
        	loop=self._player.get_loop_enabled(),
        	volume=int(self._player._get_property("volume")),
        	music_dir=self._config.music_dir,
        )
        
        self._config_store.save(config)
        
    def get_stats(self):
    	return self._stats_store.load()
    
    def load_stats(self):
        self._stats = self._stats_store.load() or Stats()


    def save_stats(self):
        self._stats_store.save(self._stats)


    def update_stats(
        self,
        path: str,
        amount: float = 0.0,
        update_time_listen: bool = False,
        update_played_times: bool = False,
    ) -> None:
        if update_time_listen:
            current = self._stats.time_listen_per_song.get(path, 0.0)
            self._stats.time_listen_per_song[path] = current + amount

        if update_played_times:
            current = self._stats.played_times_per_song.get(path, 0)
            self._stats.played_times_per_song[path] = current + 1

        self._stats.last_played = path


    def has_last_played_changed(self):
        current_song = self._get_current_song()

        if current_song is None:
            return False

        return self._stats.last_played != str(current_song.path)

    def _start_tracking_song(self, song) -> None:
        self._tracked_song_path = str(song.path)
        self._current_track_listened_seconds = 0.0
        self._current_track_play_counted = False

        self._current_track_duration = song.duration

        self._last_sample_position = None
        self._last_sample_path = self._tracked_song_path


    def _increment_play_count(self, path: str) -> None:
        self.update_stats(
        	path,
        	update_played_times=True,
        )
        self._stats.last_played = path
        self._current_track_play_counted = True


    def track_listening(self, elapsed: float) -> None:
        if elapsed <= 0:
            return

        song = self._get_current_song()

        if song is None or not self.is_playing():
            self._last_sample_position = None
            self._last_sample_path = None
            return

        path = str(song.path)

        if path != self._tracked_song_path:
            self._start_tracking_song(song)
            
        if self._current_track_duration is None:
        	self._current_track_duration = song.duration

        try:
            position = self._player.playback_position[1]
            speed = float(self._player._get_property("speed") or 1.0)
        except (MPVCommandError, RuntimeError, TypeError, ValueError):
            self._last_sample_position = None
            self._last_sample_path = None
            return

        previous_position = self._last_sample_position
        previous_path = self._last_sample_path

        self._last_sample_position = position
        self._last_sample_path = path
        
        if previous_position is None or previous_path != path:
            return

        expected_advance = elapsed * speed
        actual_advance = position - previous_position
        tolerance = max(1.0, expected_advance * 0.5)

        if actual_advance < 0:
        	is_restart = (
        		previous_position > 2.0
        		and position <= 2.0
        		and previous_path == path
        	)
        	if is_restart:
        		self._current_track_listened_seconds = 0.0
        		self._current_track_play_counted = False
        		return
        	
        	if abs(actual_advance - expected_advance) > tolerance:
        		return
        		
        self.update_stats(
            path,
            amount=elapsed,
            update_time_listen=True,
        )

        self._current_track_listened_seconds += elapsed

        duration = self._current_track_duration

        if self._current_track_play_counted:
            return

        if duration is not None and 0 < duration < PLAY_THRESHOLD:
            return

        if self._current_track_listened_seconds >= PLAY_THRESHOLD:
            self._increment_play_count(path)
            
    def handle_track_end(
    	self,
    	reason: str,
    	playlist_position: int | None = None,
    ) -> None:
        queue = self.get_queue_songs()
        if playlist_position is None or not 0 <= playlist_position < len(queue):
        	return
        	
        song = queue[playlist_position]
        path = str(song.path)
        if path != self._tracked_song_path:
        	return
        
        path = self._tracked_song_path
        duration = self._current_track_duration

        if path is None or self._current_track_play_counted:
            return

        if reason != "eof":
            return

        if duration is None or duration <= 0 or duration >= PLAY_THRESHOLD:
            return

        tolerance = self.STATS_SAMPLE_INTERVAL

        if (
            self._current_track_listened_seconds >= duration - tolerance
            and self._last_sample_path == path
        ):
            self._increment_play_count(path)
    
    def _get_current_song(self):
    	queue = self.get_queue_songs()
    	
    	if not queue:
    		return None
    	
    	pos = self._player.playlist_position
    	
    	if pos is None:
    		return None
    	
    	if pos < 0 or pos >= len(queue):
    		return None
    	
    	return queue[pos]
    
    def _get_source_songs(self) -> list[Song]:
    	current = self._get_current_song()
    	
    	if current is None:
    		return []
    	
    	if self._config.global_shuffle:
    		return [
    			song
    			for playlist in self._library.playlists
    			for song in playlist.songs
    		]
    	
    	playlist = self._library.get_playlist_by_path(Path(current.path).parent)
    	
    	if playlist is None:
    		return []
    	
    	return list(playlist.songs)
    	
    def _reset_cycle(self):
    	self._cycle.clear()
    	self._cycle_used.clear()

    
    def _create_cycle(self, first_song: Song | None = None):
    	songs = self._get_source_songs()
    	
    	if not songs:
    		self._cycle = []
    		return
    		
    	available = [
    		song
    		for song in songs
    		if song.path not in self._cycle_used
    	]
    	
    	if not available:
    	   self._cycle_used.clear()
    	   available = list(songs)
    	
    	if self._config.shuffle:
    		random.shuffle(available)    		
    	elif first_song is not None:
    		try:
    			start = next(
    				i for i, song in enumerate(available)
    				if song.path == first_song.path
    			)
    		except StopIteration:
    			start = 0
    		available = available[start:] + available[:start]
    	
    	self._cycle = available[:QUEUE_SIZE]
    	
    	for song in self._cycle:
    		self._cycle_used.add(song.path)
    
    def _select_songs(self, amount: int) -> list[Song]:
    	selected = []
    	
    	while len(selected) < amount:
    		if not self._cycle:
    			self._create_cycle()
    			
    		if not self._cycle:
    			break
    		
    		remaining = amount - len(selected)
    		take = min(remaining, len(self._cycle))
    		
    		selected.extend(self._cycle[:take])
    		del self._cycle[:take]
    	
    	return selected
    	
    def _select_sequential(
        self,
        songs: list[Song],
        start_song: Song | None = None,
        amount: int = QUEUE_SIZE,
        exclude_paths: set | None = None,
        include_start: bool = False,
    ) -> list[Song]:
        if not songs or amount <= 0:
            return []

        excluded = exclude_paths or set()

        start = 0

        if start_song is not None:
            index = next(
                (
                    i for i, song in enumerate(songs)
                    if song.path == start_song.path
                ),
                -1,
            )

            if index >= 0:
                start = index if include_start else index + 1

        selected = []

        for offset in range(len(songs)):
            song = songs[(start + offset) % len(songs)]

            if song.path in excluded:
                continue

            selected.append(song)

            if len(selected) >= amount:
                break

        return selected

    
    def should_extend_queue(self, threshold=QUEUE_SIZE):
    	queue = self.get_queue_songs()
    	playlist_index = self._player.playlist_position
    	
    	if not queue or playlist_index is None:
    		return True
    	
    	return playlist_index >= len(queue) - threshold
    
    def extend_queue(self):
        old_queue = self.get_queue_songs()

        if not old_queue:
            return

        current = self._get_current_song()
        
        if current is None:
            return

        if self._config.global_shuffle:
            songs = [
                song
                for playlist in self._library.playlists
                for song in playlist.songs
            ]
        else:
            playlist = self._library.get_playlist_by_path(Path(current.path).parent) 
            if playlist is None:
                return
            songs = list(playlist.songs)

        if not songs:
            return

        
        pos, time = self._player.playback_position
        queued_paths = {
        	song.path 
        	for song in old_queue[pos + 1:]
        }

        self._cycle_used.update(queued_paths)

        if self._config.shuffle:
            self._cycle = [
                song
                for song in self._cycle
                if song.path not in queued_paths
            ]

            new_queue = self._select_songs(QUEUE_SIZE)

        else:
            self._cycle = []

            new_queue = self._select_sequential(
                songs,
                start_song=old_queue[-1],
                amount=QUEUE_SIZE,
                exclude_paths=queued_paths,
            )

        if not new_queue:
            return

        for song in new_queue:
            self._player.append(song)

        self._cycle_used.update(
            song.path for song in new_queue
        )

        updated_queue = old_queue + new_queue
        pos, time = self._player.playback_position

        self._update_session(
            queue=updated_queue,
            pos=pos,
            time=time,
        )
        self.save_session()
    	
    
    def get_playback_state(self) -> PlaybackState:
        queue = self.get_queue_songs()

        song = None
        playlist = None
        pos = self._player.playlist_position

        if pos is not None and 0 <= pos < len(queue):
            song = queue[pos]
            if song:
            	playlist = self._library.get_playlist_by_path(Path(song.path).parent)
            	
        return self._player.state(
            song,
            queue,
            self._player.get_loop_enabled(),
            self._config.shuffle,
            self._config.global_shuffle,
            playlist,
        )
    	
    def process_playback(self):
        self._player.process_events()

        for event in self._player.consume_end_file_events():
            self.handle_track_end(
                reason=event.get("reason"),
                playlist_position=event.get("playlist_position"),
            )
    	
    def _process_queue(self):
        if self.should_extend_queue():
        	self.extend_queue()
    
    ######
    ##PLAYER COMMUNICATION##
    ######
    
    def back(self, value: float = 10):
    	self._player.seek_relative(-value)
    
    def advance(self, value: float = 10):
    	self._player.seek_relative(value)
    	
    def increase_speed(self, value: float = 0.5):
    	self._player.increase_speed(value)
    	
    def diminue_speed(self, value: float = 0.5):
    	self._player.increase_speed(-value)
    	
    def restart(self):
        self._player.seek_absolute(0)        
       
    def loop(self):
    	current = self._player.get_loop_enabled()
    	new_value = not current
    	self._player.loop_current(new_value)    	
    	self._save_config()
    	return new_value
    	
    def shuffle(self):
    	self._config.shuffle = not self._config.shuffle
    	self._save_config()
    	return self._config.shuffle
    	
    def global_shuffle(self):
    	self._config.global_shuffle = not self._config.global_shuffle
    	self._save_config()
    	return self._config.global_shuffle
        
    def pause(self):
        self._player.pause()
        return self._player.is_paused

    def next(self):
        self._player.next()

    def previous(self):
        self._player.previous()

    def increase_volume(self, value):
        self._player.increase_volume(value)
        self._save_config()
    	
    def set_volume(self, value):
    	if value > LIMIT_VOLUME:
    		raise ValueError(f"Max volume: {LIMIT_VOLUME}")
    	self._player.volume(value)
    	self._save_config()
    
    def stop(self):
    	
    	session = self._session
    	
    	if session is None or not session.queue:
    	   self._player.stop()
    	   return
    	
    	pos, time = self._player.playback_position
    	
    	self.refresh_session()
    	self.save_session()
    	
    	self._player.stop()
    
    ######
    ##PLAY##
    ######
    
    def _resume(self):
    	session = self._session_store.load()
    	
    	if session is None:
    		return
    	
    	queue = tuple(
    		self._library.get_song_by_path(path)
    		for path in session.queue
    	)
    		
    	if any(song is None for song in queue):
    	       raise RuntimeError("Could not restore saved queue")
    	       
    	if not queue:
    		return
    	
    	self._player.play(
    		queue,
    		playlist_index=session.pos,
    		time=session.time,
    	)
    
    def _play_song(
        self,
        query: str=None,
        queue: list[str]=None,
        shuffle: bool=None,
        global_shuffle: bool=None,
    ):
        # select the initial song
        if not query:
        	song = random.choice(self._library.songs)
        
        else:
        	song = self._library.get_song(query)
        
        # generate a queue if it does not exist
        if not queue:
        	# gets a playlist
        	if global_shuffle:
        		playlist = [
        			song
        			for playlist in self._library.playlists
        			for song in playlist.songs
        		]        		
        	else:
        		playlist = self._library.get_playlist_by_path(Path(song.path).parent)     
        		        	
        	# normalize playlist songs
        	playlist_songs = playlist if isinstance(playlist, list) else playlist.songs
        	# shuffle or not
        	if shuffle:
        		ordered_songs = random.sample(
        			playlist_songs,
        			k=len(playlist_songs),
        		)
        		index = ordered_songs.index(song)
        		ordered_songs = (
        			ordered_songs[index:]
        			+ ordered_songs[:index]
        		)
        		new_queue = ordered_songs[:QUEUE_SIZE]
        	else:
        		new_queue = self._select_sequential(
        			playlist_songs,
        			start_song=song,
        			amount=QUEUE_SIZE,
        			include_start=True,
        		)
        
        self._cycle_used.update(
        	song.path for song in new_queue
        )
        
        self._update_session(
        	new_queue,
        	pos=0,
        	time=0,
        )
        self.save_session()
        
        self._player.play(new_queue)
        if self._player.is_paused:
        	self.pause()
        

    def _play_playlist(
        self,
        query: str,
        shuffle: bool,
        global_shuffle: bool,
    ):
    	# similar to _play_song, but simpler, because works with playlists only

        # gets the playlist
        if global_shuffle:
        	playlist = [song for song in self._library.songs]
        else:
        	playlist = self._library.get_playlist(query)
        
        
        # normalize playlist songs
        playlist_songs = playlist if isinstance(playlist, list) else playlist.songs
        # if shuffle, randomize the playlist
        if shuffle:
        	queue = tuple(
        		random.sample(
        			playlist_songs,
        			k=min(QUEUE_SIZE, len(playlist_songs)),
        		)
        	)
        else:
        	queue = self._select_sequential(
        		playlist_songs,
        		amount=QUEUE_SIZE,
        	)
        	
        self._cycle_used.update(
        	song.path for song in queue
        )
        
        self._update_session(
        	queue,
        	pos=0,
        	time=0,
        )
        self.save_session()
        
        self._player.play(queue)
        if self._player.is_paused:
        	self.pause()
    
        
    def play(
        self,
        target: str = None,
        shuffle: bool | None = None,
        global_shuffle: bool | None = None,
        resume: bool = False,
    ):
        self._library.scan()
        	
        if shuffle is not None:
            self._config.shuffle = shuffle

        if global_shuffle is not None:
            self._config.global_shuffle = global_shuffle

        self._save_config()

        if resume and self.get_queue_songs():
            self._resume()
            return

        self._reset_cycle()

        if target is None:
            self._play_song(
                shuffle=self._config.shuffle,
                global_shuffle=self._config.global_shuffle,
            )
            return

        if target["type"] == "song":
            self._play_song(
                target["name"],
                shuffle=self._config.shuffle,
                global_shuffle=self._config.global_shuffle,
            )
            return

        if target["type"] == "playlist":
            self._play_playlist(
                target["name"],
                shuffle=self._config.shuffle,
                global_shuffle=self._config.global_shuffle,
            )
            return

        raise ValueError(
            f"Unknown play target type: {target['type']}"
        )