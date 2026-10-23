from random import random
from pmp.library.library import MusicLibrary
from pmp.library.models import Playlist, Song


class SearchEngine:

    def __init__(self, library: MusicLibrary):
        self._library = library

    def songs(self, query: str) -> list[Song]:
        """
        Procura músicas pelo título ou autor.
        """
        
        if not query:
        	return self._library.songs

        query = query.lower()

        results: list[Song] = []

        for song in self._library.songs:

            title = song.title.lower()
            author = song.artist.lower()

            if (
                query in title
                or query in author
            ):
                results.append(song)

        return results


    def playlists(self, query: str) -> list[Playlist]:
        """
        Procura playlists pelo nome.
        """
        
        if not query:
        	return self._library.playlists

        query = query.lower()

        results: list[Playlist] = []

        for playlist in self._library.playlists:

            if query in playlist.name.lower():
                results.append(playlist)

        return results


    def all(self, query: str) -> tuple[list[Song], list[Playlist]]:
        """
        Procura em músicas e playlists.
        """

        return (
            self.songs(query),
            self.playlists(query),
        )