from pmp.library.models import Playlist
from pmp.library.models import Song


class PlayResolver:
    def __init__(self, search, selector):
        self._search = search
        self._selector = selector

    def resolve(self, query):
        songs = self._search.songs(query)
        playlists = self._search.playlists(query)

        if len(songs) == 1 and not playlists:
            return songs[0]

        if len(playlists) == 1 and not songs:
            return playlists[0]

        if not songs and not playlists:
            raise ValueError(
                f"No song or playlist found: {query}"
            )

        return self._selector.choose(
            songs + playlists
        )

    def serialize(self, target):
        if isinstance(target, Song):
            return {
                "type": "song",
                "name": target.title,
            }

        if isinstance(target, Playlist):
            return {
                "type": "playlist",
                "name": target.name,
            }

        raise TypeError(
            f"Unsupported play target: {type(target).__name__}"
        )