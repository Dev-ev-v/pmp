import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from pmp.domain.source_selection import SourceSelection
from pmp.domain.track_ordering import TrackOrdering
from pmp.library.models import Playlist, Song
from pmp.playback.source_selector import SourceSelector
from pmp.storage.stats import Stats


class FakeLibrary:
    def __init__(self, playlists, root_songs=None):
        self._playlists = playlists
        self._root_songs = root_songs or []

    @property
    def playlists(self):
        return list(self._playlists)

    @property
    def root_songs(self):
        return list(self._root_songs)

    @property
    def songs(self):
        songs = list(self._root_songs)
        for playlist in self._playlists:
            songs.extend(playlist.songs)
        return songs


class SourceSelectorTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = TemporaryDirectory()
        root = Path(self.temp_dir.name)

        self.rock = [
            Song("Rock 1", root / "Rock" / "rock1.mp3"),
            Song("Rock 2", root / "Rock" / "rock2.mp3"),
        ]
        self.jazz = [
            Song("Jazz 1", root / "Jazz" / "jazz1.mp3"),
            Song("Jazz 2", root / "Jazz" / "jazz2.mp3"),
        ]
        self.classical = [
            Song("Classical 1", root / "Classical" / "classical1.mp3"),
            Song("Classical 2", root / "Classical" / "classical2.mp3"),
        ]

        playlists = [
            Playlist("Rock", tuple(self.rock), root / "Rock"),
            Playlist("Jazz", tuple(self.jazz), root / "Jazz"),
            Playlist("Classical", tuple(self.classical), root / "Classical"),
        ]
        self.library = FakeLibrary(playlists)
        self.selector = SourceSelector(self.library)
        self.stats = Stats()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_playlist_source_stays_inside_current_playlist(self):
        first = self.rock[0]
        self.selector.register_selected(first, SourceSelection.playlist)

        selected = self.selector.select(
            SourceSelection.playlist,
            first,
            1,
            TrackOrdering.sequential,
            self.stats,
        )

        self.assertEqual(selected, [self.rock[1]])

    def test_universal_rotates_between_playlists(self):
        first = self.rock[0]
        self.selector.register_selected(first, SourceSelection.universal)

        selected = self.selector.select(
            SourceSelection.universal,
            first,
            2,
            TrackOrdering.sequential,
            self.stats,
        )

        self.assertEqual(selected, [self.jazz[0], self.classical[0]])

        more = self.selector.select(
            SourceSelection.universal,
            selected[-1],
            3,
            TrackOrdering.sequential,
            self.stats,
        )

        self.assertEqual(more, [self.rock[1], self.jazz[1], self.classical[1]])

    def test_universal_does_not_repeat_current_song_in_same_batch(self):
        one_song = [self.rock[0]]
        library = FakeLibrary([
            Playlist("Rock", tuple(one_song), self.rock[0].path.parent)
        ])
        selector = SourceSelector(library)
        selector.register_selected(one_song[0], SourceSelection.universal)

        selected = selector.select(
            SourceSelection.universal,
            one_song[0],
            3,
            TrackOrdering.sequential,
            self.stats,
        )

        self.assertEqual(selected, [])

    def test_smart_initial_song_is_also_selected_by_statistics(self):
        self.stats.played_times_per_song = {
            str(self.rock[0].path): 100,
            str(self.rock[1].path): 20,
            str(self.jazz[0].path): 1,
            str(self.jazz[1].path): 10,
            str(self.classical[0].path): 5,
            str(self.classical[1].path): 30,
        }

        selected = self.selector.choose_initial(
            SourceSelection.smart,
            TrackOrdering.sequential,
            self.stats,
        )

        self.assertEqual(selected, self.jazz[0])

    def test_smart_prefers_less_played_songs(self):
        first = self.rock[0]
        self.selector.register_selected(first, SourceSelection.smart)
        self.stats.played_times_per_song = {
            str(self.rock[0].path): 100,
            str(self.rock[1].path): 20,
            str(self.jazz[0].path): 1,
            str(self.jazz[1].path): 10,
            str(self.classical[0].path): 5,
            str(self.classical[1].path): 30,
        }

        selected = self.selector.select(
            SourceSelection.smart,
            first,
            1,
            TrackOrdering.sequential,
            self.stats,
        )

        self.assertEqual(selected, [self.jazz[0]])


if __name__ == "__main__":
    unittest.main()
