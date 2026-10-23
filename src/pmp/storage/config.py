from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class UserConfig:
    shuffle: bool = False
    global_shuffle: bool = False
    loop: bool = False
    volume: int = 100
    music_dir: Path | None = None