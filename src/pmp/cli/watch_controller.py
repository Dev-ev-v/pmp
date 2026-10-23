from dataclasses import dataclass
from typing import Callable

from pmp.ipc.client import IPCClient


@dataclass(frozen=True)
class KeyBinding:
    key: str
    label: str
    action: Callable[[], bool]


class WatchController:
    def __init__(self, playback):
        self._playback = playback
        self._running = True
        self._client = IPCClient()

        self._bindings = {
            "q": KeyBinding("q", "Quit", self.quit),
            " ": KeyBinding("Space", "Pause", self.pause),

            "l": KeyBinding("l", "Loop", self.loop),

            "b": KeyBinding("b", "-10s", self.back),
            "B": KeyBinding("B", "-60s", self.back_long),
            "a": KeyBinding("a", "+10s", self.advance),
            "A": KeyBinding("A", "+60s", self.advance_long),
            
            "s": KeyBinding("s", "Shuffle", self.shuffle),
            "g": KeyBinding("g", "Global Shuffle", self.global_shuffle),
            
            "i": KeyBinding("i", "+0.25x", self.increase_speed),
            "d": KeyBinding("d", "-0.25x", self.diminue_speed),

            "UP": KeyBinding("↑", "+Volume", self.volume_up),
            "DOWN": KeyBinding("↓", "-Volume", self.volume_down),

            "LEFT": KeyBinding("←", "Previous", self.previous),
            "RIGHT": KeyBinding("→", "Next", self.next),
        }

    @property
    def bindings(self):
        return tuple(self._bindings.values())

    @property
    def running(self):
        return self._running

    def execute(self, key: str) -> bool:
        binding = self._bindings.get(key)

        if binding is None:
            return True

        return binding.action()

    def quit(self):
        self._running = False
        return False

    def pause(self):
        self._client.send("pause")
        return True

    def loop(self):
        self._playback.loop()
        return True

    def back(self):
        self._playback.back(10)
        return True

    def back_long(self):
        self._playback.back(60)
        return True

    def advance(self):
        self._playback.advance(10)
        return True

    def advance_long(self):
        self._playback.advance(60)
        return True
        
    def increase_speed(self):
        self._playback.increase_speed(0.25)
        return True
        
    def diminue_speed(self):
        self._playback.diminue_speed(0.25)
        return True
        
    def shuffle(self):
    	self._client.send("shuffle")
    	return True
    	
    def global_shuffle(self):
    	self._client.send("global_shuffle")
    	return True

    def volume_up(self):
        self._playback.increase_volume(5)
        return True

    def volume_down(self):
        self._playback.increase_volume(-5)
        return True

    def previous(self):
        self._client.send("previous")
        return True

    def next(self):
        self._client.send("next")
        return True