import math
from pathlib import Path
from mutagen import File as MutagenFile
from mutagen import MutagenError

from pmp.config import Config
from pmp.library.models import Playlist, Song


SONG_EXTENSIONS = {
    ".mp3",
    ".m4a",
    ".flac",
    ".ogg",
    ".wav",
}


class MusicLibrary:
    """
    Responsible for discovering songs and playlists.

    It does not play music.
    It does not communicate with the mpv.
    It merely represents the library.
    """

    def __init__(self, config: Config):
        self._config = config
        self._music_dir = (
        	Path(config.music_dir)
        	if config.music_dir is not None
        	else None
        )
        self._songs: list[Song] = []
        self._playlists: list[Playlist] = []
        
        self._scan_errors: list[tuple[Path, str]] = []
        
        self._songs_by_path = {}
        self._playlists_by_path = {}

        self.scan()
        
    @property
    def scan_errors(self) -> list[tuple[Path, str]]:
        return self._scan_errors.copy()
        
    @property
    def music_dir_exists(self):
    	return self._music_dir is not None and self._music_dir.is_dir()

    def scan(self) -> None:
        """Loads library songs"""
        self._songs.clear()
        self._playlists.clear()
        self._scan_errors.clear()

        if not self.music_dir_exists:
        	return

        for directory in sorted(self._music_dir.iterdir()):
            if not directory.is_dir():
                continue

            songs: list[Song] = []

            for file in sorted(directory.rglob("*")):
                if not file.is_file():
                    continue

                if file.suffix.lower() not in SONG_EXTENSIONS:
                    continue

                duration = self._inspect_audio(file)
                if duration is None:
                	continue
                
                song = Song(
                    title=file.stem,
                    artist="Unknown Artist",
                    album=None,
                    path=file,
                    duration=self._inspect_audio(file),
                )

                songs.append(song)
                self._songs.append(song)

            if songs:
                self._playlists.append(
                    Playlist(
                        name=directory.name,
                        songs=tuple(songs),
                        path=directory,
                    )
                )
            
        self._songs_by_path = {
        	song.path.resolve(): song
        	for song in self._songs
        }
        
        self._playlists_by_path = {
        	playlist.path.resolve(): playlist
        	for playlist in self._playlists
        }

    def _inspect_audio(self, path: Path) -> float | None:
        try:
            audio = MutagenFile(path)

            if audio is None or audio.info is None:
                self._scan_errors.append(
                    (path.parent.name+"/"+path.name, "Not identified format or invalid file")
                )
                return None

            duration = float(audio.info.length)

            if not math.isfinite(duration) or duration <= 0:
                self._scan_errors.append(
                    (path, "Missing or invalid duration")
                )
                return None

            return duration

        except (MutagenError, OSError, EOFError, ValueError, TypeError, OverflowError):
            self._scan_errors.append(
                (path, "The audio file could not be analyzed")
            )
            return None
    
    def get_song_by_path(self, path: Path) -> Song | None:
    	return self._songs_by_path.get(path.resolve())

    def get_playlist_by_path(self, path: Path) -> Playlist | None:
        return self._playlists_by_path.get(path.resolve())

    @property
    def songs(self) -> list[Song]:
        return self._songs.copy()

    @property
    def playlists(self) -> list[Playlist]:
        return self._playlists.copy()

    def get_song(self, title: str) -> Song | None:
        title = title.casefold()

        for song in self._songs:
            if song.title.casefold() == title:
                return song

        return None

    def get_playlist(self, name: str) -> Playlist | None:
        name = name.casefold()

        for playlist in self._playlists:
            if playlist.name.casefold() == name:
                return playlist

        return None

    def __iter__(self):
        return iter(self._songs)

    def __len__(self) -> int:
        return len(self._songs)