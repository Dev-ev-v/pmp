import json
from pathlib import Path

from pmp.storage.session import PlaybackSession


class SessionStore:

    def __init__(self, path: Path):
        self._path = path

    def save(
        self,
        session: PlaybackSession,
    ):
        data = {
            "queue": [
                str(song)
                for song in session.queue
            ],
            "pos": session.pos,
            "time": session.time,
        }

        self._path.write_text(
            json.dumps(data, indent=2)
        )

    def load(self) -> PlaybackSession:

        if not self._path.exists():
            return None

        data = json.loads(
            self._path.read_text()
        )

        return PlaybackSession(
            queue=[
                Path(song)
                for song in data["queue"]
            ],
            pos=data.get("pos", 0),
            time=data.get("time", 0),
        )