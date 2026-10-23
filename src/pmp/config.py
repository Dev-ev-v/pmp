from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True, frozen=True)
class Config:
    music_dir: Path | None
    socket_path: Path
    mpv_binary: str = "mpv"