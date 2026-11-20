import random
from pathlib import Path

from pmp.library.library import MusicLibrary
from pmp.library.models import Song
from pmp.player.player import Player
from pmp.presentation.state import PlaybackState

from pmp.storage.session import PlaybackSession
from pmp.storage.config import UserConfig
from pmp.storage.stats import Stats

from pmp.domain.source_selection import SourceSelection
from pmp.domain.track_ordering import TrackOrdering

from pmp.player.exceptions import MPVCommandError

from pmp.services.exceptions import (
    SongNotFoundError,
    PlaylistNotFoundError,
)
from pmp.playback.source_selector import SourceSelector

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
        self._stats = self._stats_store.load() or Stats()
        self.set_volume(self._config.volume)
        self._save_config()
        
        self._source_selector = SourceSelector(self._library)
        
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
    
    def _is_root_song(self, song: Song) -> bool:
    	music_dir = Path(self._config.music_dir).resolve()
    	song_parent = Path(song.path).resolve().parent
    	
    	return song_parent == music_dir
    
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
            source_selection=self._config.source_selection,
            track_ordering=self._config.track_ordering,
        	loop=self._player.get_loop_enabled(),
        	volume=int(self._player._get_property("volume")),
        	music_dir=self._config.music_dir,
        )
        
        self._config_store.save(config)
        
    def get_stats(self):
    	return self._stats
    
    def load_stats(self):
        self._stats = self._stats_store.load() or Stats()


    def save_stats(self):
        self._stats_store.save(self._stats)

    def update_time_listen(self, path: str, amount: float=0.0):
    	current = self._stats.time_listen_per_song.get(path, 0.0)
    	self._stats.time_listen_per_song[path] = current + amount
    	self._stats.last_played = path
    	
    def update_played_times(self, path: str):
    	current = self._stats.played_times_per_song.get(path, 0)
    	self._stats.played_times_per_song[path] = current + 1
    	
    def update_selection_counts(self, path: str):
    	current = self._stats.song_selection_counts.get(path, 0)
    	self._stats.song_selection_counts[path] = current + 1

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
        self.update_played_times(path)
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
        		
        self.update_time_listen(path, amount=elapsed)

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

        pos, _ = self._player.playback_position

        queued_paths = {
            song.path
            for song in old_queue[pos + 1:]
        }

        new_queue = self._source_selector.select(
            source=self._config.source_selection,
            current_song=old_queue[-1],
            amount=QUEUE_SIZE,
            ordering=self._config.track_ordering,
            stats=self._stats,
            exclude_paths=queued_paths,
        )

        if not new_queue:
            return

        # Add the selected tracks to the actual MPV playlist.
        for song in new_queue:
            self._player.append(song)

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
            	if self._is_root_song(song):
            		playlist = None
            	else:
            		playlist = self._library.get_playlist_by_path(Path(song.path).parent)
            	
        return self._player.state(
            song,
            queue,
            self._player.get_loop_enabled(),
            self._config.source_selection,
            self._config.track_ordering,
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
    	
    def set_source(self, source: SourceSelection):
        source = SourceSelection(source)
        self._config.source_selection = source

        # Keep the already queued tracks, but rebuild selector state so that
        # newly appended tracks follow the newly selected source.
        queue = self.get_queue_songs()
        if queue:
            self._source_selector.restore(queue, source)
        else:
            self._source_selector.reset()

        self._save_config()
        return self._config.source_selection

    def source_selection(self):
        options = list(SourceSelection)
        current = SourceSelection(self._config.source_selection)
        index = options.index(current)
        return self.set_source(options[(index + 1) % len(options)])

    def set_order(self, order: TrackOrdering):
        self._config.track_ordering = order
        self._save_config()
        return self._config.track_ordering

    def track_ordering(self):
        options = list(TrackOrdering)
        current = self._config.track_ordering
        index = options.index(TrackOrdering(current))

        self._config.track_ordering = options[(index + 1) % len(options)].value
        self._save_config()
        return self._config.track_ordering
        
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

        self._source_selector.restore(
            queue,
            SourceSelection(self._config.source_selection),
        )
        self._player.play(
            queue,
            playlist_index=session.pos,
            time=session.time,
        )
        if self._player.is_paused:
            self.pause()

    def _play_song(
        self,
        query: str = None,
        source_selection: SourceSelection = None,
        track_ordering: TrackOrdering = None,
    ):
        source = SourceSelection(source_selection or self._config.source_selection)
        ordering = TrackOrdering(track_ordering or self._config.track_ordering)

        if query is None:
            song = self._source_selector.choose_initial(
                source,
                ordering,
                self._stats,
            )
        else:
            song = self._library.get_song(query)

        if song is None:
            raise SongNotFoundError(query or "The music library is empty")

        self._source_selector.register_selected(song, source)
        remaining = self._source_selector.select(
            source=source,
            current_song=song,
            amount=QUEUE_SIZE - 1,
            ordering=ordering,
            stats=self._stats,
        )
        new_queue = (song, *remaining)

        if query is not None:
        	self.update_selection_counts(str(song.path))

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
        query: str = None,
        source_selection: SourceSelection = None,
        track_ordering: TrackOrdering = None,
    ):
        playlist = self._library.get_playlist(query) if query else None
        if playlist is None:
            raise PlaylistNotFoundError(query or "No playlist specified")
        if not playlist.songs:
            raise PlaylistNotFoundError(f"Playlist is empty: {query}")

        source = SourceSelection(source_selection or self._config.source_selection)
        ordering = TrackOrdering(track_ordering or self._config.track_ordering)

        # The requested playlist determines the starting song. The configured
        # source determines where subsequent songs are selected from.
        first_song = (
            random.choice(playlist.songs)
            if ordering == TrackOrdering.random
            else playlist.songs[0]
        )
        self._source_selector.register_selected(first_song, source)
        remaining = self._source_selector.select(
            source=source,
            current_song=first_song,
            amount=QUEUE_SIZE - 1,
            ordering=ordering,
            stats=self._stats,
        )
        queue = (first_song, *remaining)

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
        source_selection: SourceSelection =None,
        track_ordering: TrackOrdering =None,
        resume: bool = False,
    ):
        self._library.scan()
        	
        if source_selection is not None:
            self._config.source_selection = source_selection

        if track_ordering is not None:
            self._config.track_ordering = track_ordering

        self._save_config()

        if resume and self.get_queue_songs():
            self._resume()
            return

        self._source_selector.reset()

        if target is None:
            self._play_song(
                source_selection=self._config.source_selection,
                track_ordering=self._config.track_ordering,
            )
            return

        if target["type"] == "song":
            self._play_song(
                target["name"],
                source_selection=self._config.source_selection,
                track_ordering=self._config.track_ordering,
            )
            return

        if target["type"] == "playlist":
            self._play_playlist(
                target["name"],
                source_selection=self._config.source_selection,
                track_ordering=self._config.track_ordering,
            )
            return

        raise ValueError(
            f"Unknown play target type: {target['type']}"
        )