from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class PlaybackState:
    title: str |None = None
    artist: str |None = None
    album: str |None = None
    playlist: str |None = None

    position: float = 0
    duration: float = 0
    
    speed: float = 1.0
    volume: int = 100
    paused: bool = False
    
    queue: list[str] = None
    playlist_position: int = 0
    path: Path = None
    
    loop: bool = False
    shuffle: bool = False
    global_shuffle: bool = False