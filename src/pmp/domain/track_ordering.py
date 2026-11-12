from enum import Enum

class TrackOrdering(str, Enum):
	sequential = "sequential"
	random = "random"