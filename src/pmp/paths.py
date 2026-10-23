from pathlib import Path

from platformdirs import user_cache_dir, user_data_dir


class Paths:
    def __init__(self):
        self.cache = Path(
            user_cache_dir("pmp")
        )

        self.data = Path(
            user_data_dir("pmp")
        )

        self.cache.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.data.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.session = self.cache / "session.json"
        self.config = self.data / "config.json"
        self.stats = self.data / "stats.json"
        self.log = self.data / "daemon.log"

        self.daemon_pid = self.cache / "daemon.pid"
        self.mpv_pid = self.cache / "mpv.pid"
        self.socket = self.cache / "pmp.sock"


paths = Paths()