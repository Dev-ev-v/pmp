from dataclasses import dataclass
from pathlib import Path

from pmp.domain.source_selection import SourceSelection
from pmp.domain.track_ordering import TrackOrdering

@dataclass(slots=True)
class UserConfig:
    source_selection: SourceSelection = SourceSelection.smart
    track_ordering: TrackOrdering = TrackOrdering.random
    loop: bool = False
    volume: int = 100
    music_dir: Path | None = None