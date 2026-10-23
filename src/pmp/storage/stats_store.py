import json
from pathlib import Path

from pmp.storage.stats import Stats


class StatsStore:

    def __init__(self, path: Path):
        self._path = path

    def save(self, stats: Stats):
        data = {
            "last_played": stats.last_played,
            "time_listen_per_song": stats.time_listen_per_song,
            "played_times_per_song": stats.played_times_per_song,
        }

        self._path.write_text(
            json.dumps(data, indent=2)
        )

    def load(self) -> Stats | None:
        if not self._path.exists():
            return None

        data = json.loads(
            self._path.read_text()
        )

        return Stats(
            last_played=data.get("last_played"),
            time_listen_per_song=data.get("time_listen_per_song", {}),
            played_times_per_song=data.get("played_times_per_song", {}),
        )