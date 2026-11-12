from enum import Enum

class SourceSelection(str, Enum):
	playlist = "playlist"
	universal = "universal"
	smart = "smart"