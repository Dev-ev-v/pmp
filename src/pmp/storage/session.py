from dataclasses import dataclass
from pathlib import Path


@dataclass
class PlaybackSession:

    queue: tuple[Path, ...]
    pos: int
    time: float