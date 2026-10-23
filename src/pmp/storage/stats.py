from dataclasses import dataclass, field

@dataclass
class Stats:
    last_played: str = None
    time_listen_per_song: dict = field(default_factory=dict)
    played_times_per_song: dict = field(default_factory=dict)