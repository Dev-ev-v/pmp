from abc import ABC, abstractmethod

from pmp.presentation.formatters import format_time, progress_bar
from pmp.domain.source_selection import SourceSelection
from pmp.domain.track_ordering import TrackOrdering


class Widget(ABC):

    @abstractmethod
    def render(self, state) -> str:
        ...


class StatusWidget(Widget):

    def render(self, state) -> str:
        icon = None
        if state.paused:
        	icon = "⏸" 
        	text = "Paused"
        elif not state.duration:
        	icon = "⏹️"        
        	text = "Nothing is being played"
        else:
        	icon =  "▶"
        	text = "Playing"

        return f"{icon} {text}"


class MetadataWidget(Widget):

    def render(self, state) -> str:
        artist = state.artist or "Unknown Artist"
        title = state.title or "Unknown Title"
        playlist = state.playlist or "No playlist"

        return f"🎤 {artist}\n{title}\n{playlist}"


class PositionWidget(Widget):

    def render(self, state) -> str:
        bar = progress_bar(state.position, state.duration)

        return (
            f"{format_time(state.position)} "
            f"{bar} "
            f"{format_time(state.duration)}"
        )


class VolumeWidget(Widget):

    def render(self, state) -> str:
        icon = None
        if state.volume > 60:
        	icon = "🔊"
        elif state.volume > 30:
        	icon = "🔉"
        elif state.volume > 0:
        	icon = "🔈"
        else:
        	icon = "🔇"
        return f"{icon} Volume: {state.volume}%"
        
class SpeedWidget(Widget):
	
	def render(self, state) -> str:
		return f"⏰ {state.speed}x"


class AlbumWidget(Widget):

    def render(self, state) -> str:
        if not state.album:
            return ""

        return f"💽 Album: {state.album}"
        

class LoopWidget(Widget):
	
	def render(self, state) -> str:
		icon = "✅" if state.loop else "❌"
		return f"🔂 Loop: {icon}"
		
class SourceSelectionWidget(Widget):
	
	def render(self, state) -> str:
		source_selection = state.source_selection
		icon = None
		if source_selection == SourceSelection.playlist:
			icon = "️🎶"
		if source_selection == SourceSelection.universal:					
			icon = "🌐"
		if source_selection == SourceSelection.smart:
			icon = "🤖"
		
		return f"{icon} Source: {source_selection.capitalize()}"
					

class TrackOrderingWidget(Widget):
	
	def render(self, state) -> str:
		track_ordering = state.track_ordering
		icon = None
		if track_ordering == TrackOrdering.sequential:
			icon = "⬇️ "
		if track_ordering == TrackOrdering.random:					
			icon = "🔀"
		
		return f"{icon} Track Ordering: {track_ordering.capitalize()}"	

class QueueWidget(Widget):

    def render(self, state) -> str:
        queue = state.queue

        if not state.path:
            return ""

        idx = state.playlist_position

        previous_music = queue[idx - 1] if idx > 0 else None
        next_musics = queue[idx + 1:idx + 5]

        previous = (
            previous_music["title"]
            if previous_music
            else "No previous song"
        )

        next_ = "\n".join(
            music["title"] 
            for music in next_musics
        )

        if not next_:
            next_ = "❌ No More songs"

        return (
            f"⏪ Previous\n"
            f"{previous}\n"
            f"\n⏩ Next:\n"
            f"{next_}"
        )