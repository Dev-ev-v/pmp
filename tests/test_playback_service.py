from pathlib import Path

import pytest

from pmp.domain.source_selection import SourceSelection
from pmp.domain.track_ordering import TrackOrdering
from pmp.library.models import Playlist, Song
from pmp.playback.playback import PlaybackService
from pmp.services.exceptions import SongNotFoundError
from pmp.storage.config import UserConfig
from pmp.storage.session import PlaybackSession
from pmp.storage.stats import Stats


class FakeLibrary:
    def __init__(self, playlists, root_songs=None):
        self._playlists = list(playlists)
        self._root_songs = list(root_songs or [])
        self.scan_calls = 0

    def scan(self):
        self.scan_calls += 1

    @property
    def songs(self):
        songs = list(self._root_songs)
        for playlist in self._playlists:
            songs.extend(playlist.songs)
        return songs

    @property
    def root_songs(self):
        return list(self._root_songs)

    @property
    def playlists(self):
        return list(self._playlists)

    def get_song(self, query):
        if not query:
            return None
        query = query.casefold()
        return next(
            (song for song in self.songs if song.title.casefold() == query),
            None,
        )

    def get_playlist(self, query):
        if not query:
            return None
        query = query.casefold()
        return next(
            (playlist for playlist in self._playlists
             if playlist.name.casefold() == query),
            None,
        )

    def get_song_by_path(self, path):
        target = Path(path).resolve()
        return next(
            (song for song in self.songs if song.path.resolve() == target),
            None,
        )

    def get_playlist_by_path(self, path):
        target = Path(path).resolve()
        return next(
            (playlist for playlist in self._playlists
             if playlist.path.resolve() == target),
            None,
        )


class FakePlayer:
    def __init__(self):
        self.play_calls = []
        self.append_calls = []
        self.volume_calls = []
        self.idle = True
        self.is_paused = False
        self._playlist_position = 0
        self._time_position = 0.0
        self._volume = 100
        self._speed = 1.0
        self.loop_enabled = False

    def ensure_ready(self):
        pass

    def volume(self, value):
        self._volume = value
        self.volume_calls.append(value)

    def get_loop_enabled(self):
        return self.loop_enabled

    def _get_property(self, name):
        if name == "volume":
            return self._volume
        if name == "speed":
            return self._speed
        raise AssertionError(f"Unexpected player property: {name}")

    def play(self, songs, playlist_index=0, time=0):
        self.play_calls.append((tuple(songs), playlist_index, time))
        self._playlist_position = playlist_index
        self._time_position = time
        self.idle = False

    def append(self, song):
        self.append_calls.append(song)

    @property
    def playback_position(self):
        return self._playlist_position, self._time_position

    @property
    def playlist_position(self):
        return self._playlist_position

    def set_position(self, position, time_position):
        self._playlist_position = position
        self._time_position = time_position

    def pause(self):
        self.is_paused = not self.is_paused

    def stop(self):
        self.idle = True


class FakeSessionStore:
    def __init__(self, session=None):
        self.session = session
        self.save_calls = []

    def load(self):
        return self.session

    def save(self, session):
        self.session = session
        self.save_calls.append(session)


class FakeConfigStore:
    def __init__(self, config=None):
        self.config = config or UserConfig()
        self.save_calls = []

    def load(self):
        return self.config

    def save(self, config):
        self.config = config
        self.save_calls.append(config)


class FakeStatsStore:
    def __init__(self, stats=None):
        self.stats = stats
        self.save_calls = []

    def load(self):
        return self.stats

    def save(self, stats):
        self.stats = stats
        self.save_calls.append(stats)


@pytest.fixture

def playback_environment(tmp_path):
    music_dir = tmp_path / "music"
    rock_dir = music_dir / "Rock"
    jazz_dir = music_dir / "Jazz"

    rock_songs = [
        Song(f"Rock {index}", rock_dir / f"rock{index}.mp3", duration=180)
        for index in range(1, 9)
    ]
    jazz_songs = [
        Song(f"Jazz {index}", jazz_dir / f"jazz{index}.mp3", duration=180)
        for index in range(1, 4)
    ]

    library = FakeLibrary([
        Playlist("Rock", tuple(rock_songs), rock_dir),
        Playlist("Jazz", tuple(jazz_songs), jazz_dir),
    ])
    player = FakePlayer()
    session_store = FakeSessionStore()
    config_store = FakeConfigStore(UserConfig(
        source_selection=SourceSelection.playlist,
        track_ordering=TrackOrdering.sequential,
        loop=False,
        volume=75,
        music_dir=music_dir,
    ))
    stats_store = FakeStatsStore(Stats())

    playback = PlaybackService(
        library=library,
        player=player,
        search=None,
        session_store=session_store,
        config_store=config_store,
        stats_store=stats_store,
        STATS_SAMPLE_INTERVAL=0.2,
    )

    return {
        "playback": playback,
        "library": library,
        "player": player,
        "session_store": session_store,
        "config_store": config_store,
        "stats_store": stats_store,
        "rock": rock_songs,
        "jazz": jazz_songs,
    }


def test_play_explicit_song_starts_requested_track_and_counts_only_it(
    playback_environment,
):
    env = playback_environment
    playback = env["playback"]
    player = env["player"]
    selected_song = env["rock"][1]

    playback.play({"type": "song", "name": selected_song.title})

    played_queue = player.play_calls[-1][0]
    assert played_queue[0] == selected_song
    assert played_queue == tuple(env["rock"][1:4])
    assert playback.get_stats().song_selection_counts == {
        str(selected_song.path): 1
    }
    assert env["session_store"].session.queue == [song.path for song in played_queue]


def test_play_without_explicit_target_does_not_count_a_song_selection(
    playback_environment,
):
    env = playback_environment

    env["playback"].play()

    assert env["player"].play_calls
    assert env["playback"].get_stats().song_selection_counts == {}


def test_play_playlist_starts_inside_requested_playlist_without_song_selection_count(
    playback_environment,
):
    env = playback_environment

    env["playback"].play({"type": "playlist", "name": "Rock"})

    played_queue = env["player"].play_calls[-1][0]
    assert played_queue == tuple(env["rock"][:3])
    assert env["playback"].get_stats().song_selection_counts == {}


def test_extend_queue_appends_tracks_to_player_and_persists_same_queue(
    playback_environment,
):
    env = playback_environment
    playback = env["playback"]
    player = env["player"]

    playback.play({"type": "song", "name": "Rock 1"})
    original_queue = env["session_store"].session.queue.copy()

    playback.extend_queue()

    appended = player.append_calls
    persisted_queue = env["session_store"].session.queue

    assert [song.path for song in appended] == [
        env["rock"][3].path,
        env["rock"][4].path,
        env["rock"][5].path,
    ]
    assert persisted_queue == original_queue + [song.path for song in appended]
    assert len(persisted_queue) == len(original_queue) + len(appended)
    assert playback.get_stats().song_selection_counts == {
        str(env["rock"][0].path): 1
    }



def test_changing_source_keeps_current_queue_and_changes_future_selection(
    playback_environment,
):
    env = playback_environment
    playback = env["playback"]

    playback.play({"type": "song", "name": "Rock 1"})
    current_queue = env["session_store"].session.queue.copy()

    selected_source = playback.set_source(SourceSelection.universal)

    assert selected_source == SourceSelection.universal
    assert env["session_store"].session.queue == current_queue

    playback.extend_queue()

    assert env["player"].append_calls[0] == env["jazz"][0]



def test_resume_restores_saved_queue_position_and_time(playback_environment):
    env = playback_environment
    saved_queue = [env["rock"][1].path, env["rock"][2].path]
    env["session_store"].session = PlaybackSession(
        queue=saved_queue,
        pos=1,
        time=42.5,
    )

    env["playback"].play(resume=True)

    songs, playlist_index, time_position = env["player"].play_calls[-1]
    assert songs == (env["rock"][1], env["rock"][2])
    assert playlist_index == 1
    assert time_position == 42.5


def test_long_track_is_counted_only_after_listening_threshold(playback_environment):
    env = playback_environment
    playback = env["playback"]
    player = env["player"]
    song = env["rock"][0]

    env["session_store"].session = PlaybackSession(
        queue=[song.path],
        pos=0,
        time=0,
    )
    player.idle = False

    player.set_position(0, 0)
    playback.track_listening(15)
    assert playback.get_stats().played_times_per_song == {}

    player.set_position(0, 15)
    playback.track_listening(15)
    assert playback.get_stats().played_times_per_song == {}

    player.set_position(0, 30)
    playback.track_listening(15)
    assert playback.get_stats().played_times_per_song == {str(song.path): 1}


def test_short_track_is_counted_only_after_eof_and_near_complete_listening(
    playback_environment,
):
    env = playback_environment
    playback = env["playback"]
    player = env["player"]
    song = env["rock"][0]
    song.duration = 20

    env["session_store"].session = PlaybackSession(
        queue=[song.path],
        pos=0,
        time=0,
    )
    player.idle = False

    player.set_position(0, 0)
    playback.track_listening(10)
    player.set_position(0, 10)
    playback.track_listening(10)
    player.set_position(0, 20)
    playback.track_listening(10)

    playback.handle_track_end("stop", playlist_position=0)
    assert playback.get_stats().played_times_per_song == {}

    playback.handle_track_end("eof", playlist_position=0)
    assert playback.get_stats().played_times_per_song == {str(song.path): 1}


def test_unknown_song_raises_without_starting_player(playback_environment):
    env = playback_environment

    with pytest.raises(SongNotFoundError):
        env["playback"].play({"type": "song", "name": "Missing Song"})

    assert env["player"].play_calls == []
    assert env["playback"].get_stats().song_selection_counts == {}


def test_unknown_target_type_is_rejected(playback_environment):
    env = playback_environment

    with pytest.raises(ValueError, match="Unknown play target type"):
        env["playback"].play({"type": "album", "name": "Unknown"})

    assert env["player"].play_calls == []


def test_resume_fails_when_a_saved_track_is_missing(playback_environment):
    env = playback_environment
    missing_path = env["rock"][0].path.parent / "removed-track.mp3"
    env["session_store"].session = PlaybackSession(
        queue=[missing_path],
        pos=0,
        time=12.0,
    )

    with pytest.raises(RuntimeError, match="Could not restore saved queue"):
        env["playback"].play(resume=True)

    assert env["player"].play_calls == []


def test_stop_persists_current_queue_position_and_time(playback_environment):
    env = playback_environment
    playback = env["playback"]
    player = env["player"]

    playback.play({"type": "song", "name": "Rock 1"})
    player.set_position(1, 37.5)

    playback.stop()

    saved = env["session_store"].session
    assert saved.pos == 1
    assert saved.time == 37.5
    assert saved.queue == [song.path for song in player.play_calls[-1][0]]
    assert player.idle is True


def test_paused_intervals_do_not_increase_listening_time(playback_environment):
    env = playback_environment
    playback = env["playback"]
    player = env["player"]
    song = env["rock"][0]
    env["session_store"].session = PlaybackSession(
        queue=[song.path], pos=0, time=0,
    )
    player.idle = False

    player.set_position(0, 0)
    playback.track_listening(10)  # Establish baseline.
    player.set_position(0, 10)
    playback.track_listening(10)

    player.is_paused = True
    player.set_position(0, 20)
    playback.track_listening(10)
    assert playback.get_stats().time_listen_per_song == {str(song.path): 10}

    player.is_paused = False
    playback.track_listening(10)  # Establish a new baseline after resuming.
    player.set_position(0, 30)
    playback.track_listening(10)

    assert playback.get_stats().time_listen_per_song == {str(song.path): 20}
    assert playback.get_stats().played_times_per_song == {}


def test_backward_seek_does_not_add_the_seek_distance_to_listening_time(
    playback_environment,
):
    env = playback_environment
    playback = env["playback"]
    player = env["player"]
    song = env["rock"][0]
    env["session_store"].session = PlaybackSession(
        queue=[song.path], pos=0, time=0,
    )
    player.idle = False

    player.set_position(0, 10)
    playback.track_listening(10)  # Establish baseline.
    player.set_position(0, 20)
    playback.track_listening(10)

    player.set_position(0, 5)  # Simulate seeking backwards.
    playback.track_listening(10)
    player.set_position(0, 15)
    playback.track_listening(10)

    assert playback.get_stats().time_listen_per_song == {str(song.path): 20}
    assert playback.get_stats().played_times_per_song == {}


def test_switching_tracks_resets_per_track_listening_tracking(playback_environment):
    env = playback_environment
    playback = env["playback"]
    player = env["player"]
    first_song, second_song = env["rock"][:2]
    env["session_store"].session = PlaybackSession(
        queue=[first_song.path, second_song.path], pos=0, time=0,
    )
    player.idle = False

    player.set_position(0, 0)
    playback.track_listening(10)  # Establish first-track baseline.
    player.set_position(0, 10)
    playback.track_listening(10)

    player.set_position(1, 0)
    playback.track_listening(10)  # Detect the track change.
    player.set_position(1, 10)
    playback.track_listening(10)

    assert playback.get_stats().time_listen_per_song == {
        str(first_song.path): 10,
        str(second_song.path): 10,
    }
    assert playback.get_stats().played_times_per_song == {}


def test_repeated_end_of_file_event_does_not_double_count_short_track(
    playback_environment,
):
    env = playback_environment
    playback = env["playback"]
    player = env["player"]
    song = env["rock"][0]
    song.duration = 20
    env["session_store"].session = PlaybackSession(
        queue=[song.path], pos=0, time=0,
    )
    player.idle = False

    player.set_position(0, 0)
    playback.track_listening(10)
    player.set_position(0, 10)
    playback.track_listening(10)
    player.set_position(0, 20)
    playback.track_listening(10)

    playback.handle_track_end("eof", playlist_position=0)
    playback.handle_track_end("eof", playlist_position=0)

    assert playback.get_stats().played_times_per_song == {str(song.path): 1}


def test_forward_seek_does_not_count_skipped_audio_as_listening_time(
    playback_environment,
):
    env = playback_environment
    playback = env["playback"]
    player = env["player"]
    song = env["rock"][0]
    env["session_store"].session = PlaybackSession(
        queue=[song.path], pos=0, time=0,
    )
    player.idle = False

    player.set_position(0, 10)
    playback.track_listening(10)  # Establish baseline.
    player.set_position(0, 20)
    playback.track_listening(10)

    player.set_position(0, 100)  # Simulate seeking forward.
    playback.track_listening(10)
    player.set_position(0, 180)
    playback.track_listening(10)
    player.set_position(0, 260)
    playback.track_listening(10)

    # Only the first 10 seconds were actually played. The skipped intervals
    # must not inflate listening time or trigger the play-count threshold.
    assert playback.get_stats().time_listen_per_song == {str(song.path): 10}
    assert playback.get_stats().played_times_per_song == {}
