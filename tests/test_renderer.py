from types import SimpleNamespace
from pathlib import Path

from pmp.presentation.renderer import PlaybackRenderer
from pmp.storage.stats import Stats


def test_renderer_can_be_imported():
    assert PlaybackRenderer is not None


def test_selection_only_stats_are_rendered():
    stats = Stats(
        song_selection_counts={"/music/example.mp3": 1}
    )

    output = PlaybackRenderer().render_stats(
        stats,
        get_song_by_path=lambda path: None,
        short=False,
        title=False,
    )

    assert "SONG SELECTION" in output
    assert "example.mp3" in output
    assert "No stats yet" not in output


def test_zero_duration_song_does_not_crash_play_equivalent_rendering():
    path = Path("/music/zero-duration.mp3")
    stats = Stats(
        time_listen_per_song={str(path): 10.0}
    )
    song = SimpleNamespace(title="Zero duration", duration=0)

    output = PlaybackRenderer().render_stats(
        stats,
        get_song_by_path=lambda requested_path: song,
        short=False,
        title=False,
    )

    assert "TIME LISTENED" in output
    assert "PLAY EQUIVALENTS" in output
