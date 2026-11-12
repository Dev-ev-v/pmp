import json
from pathlib import Path

from pmp.storage.config import UserConfig
from pmp.domain.source_selection import SourceSelection
from pmp.domain.track_ordering import TrackOrdering

class ConfigStore:
    def __init__(self, path: Path):
        self._path = path

    def save(self, config: UserConfig) -> None:
        data = {
            "source_selection": config.source_selection,
            "track_ordering": config.track_ordering,
            "loop": config.loop,
            "volume": config.volume,
            "music_dir": (
                str(config.music_dir)
                if config.music_dir is not None
                else None
            ),
        }

        self._path.parent.mkdir(parents=True, exist_ok=True)

        self._path.write_text(
            json.dumps(data, indent=2),
            encoding="utf-8",
        )

    def load(self) -> UserConfig:
        if not self._path.is_file():
            return UserConfig()

        data = json.loads(
            self._path.read_text(encoding="utf-8")
        )

        music_dir = data.get("music_dir")

        return UserConfig(
            source_selection=data.get("source_selection", SourceSelection.smart),
            track_ordering=data.get("track_ordering", TrackOrdering.random),
            loop=data.get("loop", False),
            volume=data.get("volume", 100),
            music_dir=(
                Path(music_dir)
                if music_dir is not None
                else None
            ),
        )