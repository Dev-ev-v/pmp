
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class Song:
    title: str
    path: Path
    artist: str | None = None
    album: str | None = None
    duration: float | None = None

    @property
    def filename(self) -> str:
        return self.path.name

    @property
    def extension(self) -> str:
        return self.path.suffix.lower()
        

@dataclass(slots=True)
class Playlist:

    name:str
    songs:tuple[Song, ...]        
    path:Path