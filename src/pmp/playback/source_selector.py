"""Source-specific song selection strategies for playback."""

from __future__ import annotations

import random
from pathlib import Path
from typing import Iterable

from pmp.domain.source_selection import SourceSelection
from pmp.domain.track_ordering import TrackOrdering
from pmp.library.library import MusicLibrary
from pmp.library.models import Song
from pmp.storage.stats import Stats


class SourceSelector:
    """Select songs according to the configured source strategy.

    ``playlist`` stays inside the current collection, ``universal`` rotates
    between collections, and ``smart`` favors less-played/less-selected songs.

    The selector keeps only transient cycle state. The playback session remains
    the source of truth and can be fed back through :meth:`restore` on resume.
    """

    def __init__(self, library: MusicLibrary):
        self._library = library
        self.reset()

    def reset(self) -> None:
        self._used_by_collection: dict[Path, set[Path]] = {}
        self._last_by_collection: dict[Path, Path] = {}
        self._smart_used: set[Path] = set()
        self._universal_index = 0

    def restore(self, songs: Iterable[Song], source: SourceSelection) -> None:
        """Rebuild transient selector state from an existing session queue."""
        self.reset()
        for song in songs:
            self.register_selected(song, source)

    def choose_initial(
        self,
        source: SourceSelection,
        ordering: TrackOrdering,
        stats: Stats,
    ) -> Song | None:
        """Choose the first track when the user did not specify a target."""
        source = SourceSelection(source)
        ordering = TrackOrdering(ordering)

        if source != SourceSelection.smart:
            songs = self._library.songs
            return random.choice(songs) if songs else None

        songs = self._library.songs
        if not songs:
            return None

        def score(song: Song) -> tuple[int, int]:
            path = str(song.path)
            played = int(stats.played_times_per_song.get(path, 0) or 0)
            selected = int(stats.song_selection_counts.get(path, 0) or 0)
            return played, selected

        best_score = min(score(song) for song in songs)
        candidates = [song for song in songs if score(song) == best_score]
        return random.choice(candidates) if ordering == TrackOrdering.random else candidates[0]

    def register_selected(
        self,
        song: Song,
        source: SourceSelection,
    ) -> None:
        """Mark a song as already selected, including an explicit play target."""
        source = SourceSelection(source)
        path = song.path.resolve()
        self._smart_used.add(path)

        collection = self._collection_for(song)
        if collection is None:
            return

        key, _ = collection
        self._used_by_collection.setdefault(key, set()).add(path)
        self._last_by_collection[key] = path

        if source == SourceSelection.universal:
            collections = self._collections()
            index = next(
                (i for i, (collection_key, _) in enumerate(collections)
                 if collection_key == key),
                None,
            )
            if index is not None and collections:
                self._universal_index = (index + 1) % len(collections)

    def select(
        self,
        source: SourceSelection,
        current_song: Song,
        amount: int,
        ordering: TrackOrdering,
        stats: Stats,
        exclude_paths: set[Path] | None = None,
    ) -> list[Song]:
        if amount <= 0 or current_song is None:
            return []

        source = SourceSelection(source)
        ordering = TrackOrdering(ordering)
        excluded = {Path(path).resolve() for path in (exclude_paths or set())}
        # The current/last queued song must never be selected again in the
        # same extension batch, even when its collection has only one track.
        excluded.add(current_song.path.resolve())

        strategies = {
            SourceSelection.playlist: self._select_playlist,
            SourceSelection.universal: self._select_universal,
            SourceSelection.smart: self._select_smart,
        }
        return strategies[source](
            current_song=current_song,
            amount=amount,
            ordering=ordering,
            stats=stats,
            excluded=excluded,
        )

    def _collections(self) -> list[tuple[Path, list[Song]]]:
        collections: list[tuple[Path, list[Song]]] = []

        root_songs = self._library.root_songs
        if root_songs:
            root_key = root_songs[0].path.parent.resolve()
            collections.append((root_key, root_songs))

        for playlist in self._library.playlists:
            if playlist.songs:
                collections.append((playlist.path.resolve(), list(playlist.songs)))

        return collections

    def _collection_for(self, song: Song) -> tuple[Path, list[Song]] | None:
        path = song.path.resolve()
        for key, songs in self._collections():
            if any(candidate.path.resolve() == path for candidate in songs):
                return key, songs
        return None

    def _available_from_collection(
        self,
        key: Path,
        songs: list[Song],
        excluded: set[Path],
    ) -> list[Song]:
        used = self._used_by_collection.setdefault(key, set())
        available = [
            song for song in songs
            if song.path.resolve() not in used
            and song.path.resolve() not in excluded
        ]

        # A collection starts a new cycle only after all its eligible songs
        # have been selected once.
        if not available:
            eligible = [
                song for song in songs
                if song.path.resolve() not in excluded
            ]
            if eligible:
                used.clear()
                available = eligible

        return available

    def _pick_from_collection(
        self,
        key: Path,
        songs: list[Song],
        ordering: TrackOrdering,
        excluded: set[Path],
    ) -> Song | None:
        available = self._available_from_collection(key, songs, excluded)
        if not available:
            return None

        if ordering == TrackOrdering.random:
            selected = random.choice(available)
        else:
            last_path = self._last_by_collection.get(key)
            if last_path is None:
                selected = available[0]
            else:
                full_index = next(
                    (i for i, song in enumerate(songs)
                     if song.path.resolve() == last_path),
                    -1,
                )
                selected = next(
                    (song for offset in range(1, len(songs) + 1)
                     if (song := songs[(full_index + offset) % len(songs)]) in available),
                    available[0],
                )

        path = selected.path.resolve()
        self._used_by_collection.setdefault(key, set()).add(path)
        self._last_by_collection[key] = path
        self._smart_used.add(path)
        return selected

    def _select_playlist(
        self,
        current_song: Song,
        amount: int,
        ordering: TrackOrdering,
        stats: Stats,
        excluded: set[Path],
    ) -> list[Song]:
        collection = self._collection_for(current_song)
        if collection is None:
            return []

        key, songs = collection
        selected: list[Song] = []
        for _ in range(amount):
            song = self._pick_from_collection(key, songs, ordering, excluded)
            if song is None:
                break
            selected.append(song)
            excluded.add(song.path.resolve())
        return selected

    def _select_universal(
        self,
        current_song: Song,
        amount: int,
        ordering: TrackOrdering,
        stats: Stats,
        excluded: set[Path],
    ) -> list[Song]:
        collections = self._collections()
        if not collections:
            return []

        selected: list[Song] = []
        checked_without_result = 0

        while len(selected) < amount and checked_without_result < len(collections):
            index = self._universal_index % len(collections)
            key, songs = collections[index]
            self._universal_index = (index + 1) % len(collections)

            song = self._pick_from_collection(key, songs, ordering, excluded)
            if song is None:
                checked_without_result += 1
                continue

            selected.append(song)
            excluded.add(song.path.resolve())
            checked_without_result = 0

        return selected

    def _select_smart(
        self,
        current_song: Song,
        amount: int,
        ordering: TrackOrdering,
        stats: Stats,
        excluded: set[Path],
    ) -> list[Song]:
        songs = self._library.songs
        selected: list[Song] = []
        pending_selections: dict[str, int] = {}

        for _ in range(amount):
            available = [
                song for song in songs
                if song.path.resolve() not in self._smart_used
                and song.path.resolve() not in excluded
            ]

            if not available:
                eligible = [
                    song for song in songs
                    if song.path.resolve() not in excluded
                ]
                if not eligible:
                    break
                self._smart_used.clear()
                available = eligible

            def score(song: Song) -> tuple[int, int]:
                path = str(song.path)
                played = int(stats.played_times_per_song.get(path, 0) or 0)
                selected_count = int(
                    stats.song_selection_counts.get(path, 0) or 0
                ) + pending_selections.get(path, 0)
                return played, selected_count

            best_score = min(score(song) for song in available)
            best_candidates = [
                song for song in available if score(song) == best_score
            ]
            if ordering == TrackOrdering.random:
                song = random.choice(best_candidates)
            else:
                song = best_candidates[0]

            path = song.path.resolve()
            self._smart_used.add(path)
            excluded.add(path)
            pending_selections[str(song.path)] = (
                pending_selections.get(str(song.path), 0) + 1
            )
            selected.append(song)

        return selected
