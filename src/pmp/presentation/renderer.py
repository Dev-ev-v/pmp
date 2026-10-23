from pathlib import Path

from pmp.presentation.formatters import format_duration
from pmp.presentation.widgets import (
    AlbumWidget,
    MetadataWidget,
    PositionWidget,
    StatusWidget,
    VolumeWidget,
    SpeedWidget,
    QueueWidget,
    LoopWidget,
    ShuffleWidget,
    GlobalShuffleWidget
)


class PlaybackRenderer:

    def __init__(self):
        self.widgets = [
            StatusWidget(),
            MetadataWidget(),
            PositionWidget(),
            VolumeWidget(),
            SpeedWidget(),
            AlbumWidget(),
            LoopWidget(),
            ShuffleWidget(),
            GlobalShuffleWidget(),
            QueueWidget(),
        ]

    def render_state(self, state) -> str:
        parts = []

        if not state.path:
            return "⏹️ No music playing"
        
        for widget in self.widgets:
            text = widget.render(state)

            if text:
                parts.append(text)
            
        return "\n\n".join(parts) 
    			
    def render_queue(self, queue, pos) -> str:
    	parts = []
    	queue = queue[pos:]
    	if not queue:
    		return
    	for song in queue:
    		if song == queue[0]:
    			parts.append(f"=> {song.title}")
    		else:
    			parts.append(song.title)
    	
    	return "\n".join(parts)
    	
    def render_library(self, playlists, scan_errors):
    	parts = []
    	total_songs = 0
    	for playlist in playlists:
        	parts.append(f"——{playlist.name}——")
        	for i, song in enumerate(playlist.songs):
        		parts.append(f"    {i + 1}: {song.title}")
        		total_songs += 1
        	parts.append("")    	
    	
    	parts.append(f"Total songs: {total_songs}")
    	
    	parts.append("")
    	parts.append("Scan Errors:")
    	for error in scan_errors:
    		parts.append(f"{error[0]}: {error[1]}")
    	
    	return "\n".join(parts) 

    def _render_stats_table(self, title, entries, value_header):
        if not entries:
            return f"  {title}\n  No data yet."

        rows = [
            (Path(song_path).name, str(value))
            for song_path, value in entries
        ]

        name_width = max(
            len("Song"),
            max(len(name) for name, _ in rows),
        )
        value_width = max(
            len(value_header),
            max(len(value) for _, value in rows),
        )

        lines = [
            f"  {title}",
            f"  {'Song':<{name_width}}  {value_header:>{value_width}}",
            f"  {'-' * name_width}  {'-' * value_width}",
        ]

        for name, value in rows:
            lines.append(
                f"  {name:<{name_width}}  {value:>{value_width}}"
            )

        return "\n".join(lines)

    def render_stats(self, stats, get_song_by_path):
        if stats is None or not (
            stats.time_listen_per_song
            or stats.played_times_per_song
        ):
            return "No stats yet. Try listening to some music."

        time_entries = sorted(
            stats.time_listen_per_song.items(),
            key=lambda item: item[1],
            reverse=True,
        )

        play_entries = sorted(
            stats.played_times_per_song.items(),
            key=lambda item: item[1],
            reverse=True,
        )        
        
        play_equivalents = stats.time_listen_per_song
        for key, value in play_equivalents.items():
        	song = get_song_by_path(Path(key))
        	if song:
        		play_equivalents[key] = round(value / song.duration, 2)
        	
        play_equivalents_list = sorted(
            play_equivalents.items(),
            key=lambda item: item[1],
            reverse=True,
        )        

        sections = [
            "PMP | STATISTICS",
            "=" * 50,
            self._render_stats_table(
                "TIME LISTENED",
                [
                    (path, format_duration(seconds))
                    for path, seconds in time_entries
                ],
                "Time",
            ),
            "",
            self._render_stats_table(
                "PLAY COUNT",
                play_entries,
                "Plays",
            ),
            "",
            self._render_stats_table(
            	"PLAY EQUIVALENTS",
            	play_equivalents_list,
            	"Equivalents",
            ),
        ]

        return "\n".join(sections)
    	
    	
    def render_controls(self, bindings):
    	parts = []
    	
    	for binding in bindings:
    		parts.append(
    			f"[{binding.key}] {binding.label}"
    		)
    	return "  ".join(parts)	