import threading
import time

import pytest

from pmp.playback.runtime import PlaybackRuntime


class FakePlayback:
    def __init__(
        self,
        *,
        process_error=None,
        ensure_error=None,
        process_gate=None,
        save_session_error=None,
        extend_queue_needed=False,
        playing=False,
    ):
        self.process_error = process_error
        self.ensure_error = ensure_error
        self.process_gate = process_gate
        self.save_session_error = save_session_error
        self.extend_queue_needed = extend_queue_needed
        self.playing = playing

        self.ensure_ready_calls = 0
        self.process_playback_calls = 0
        self.track_listening_calls = 0
        self.extend_queue_calls = 0
        self.refresh_session_calls = 0
        self.save_session_calls = 0
        self.save_stats_calls = 0

        self.process_entered = threading.Event()

    def ensure_ready(self):
        self.ensure_ready_calls += 1
        if self.ensure_error is not None:
            raise self.ensure_error

    def process_playback(self):
        self.process_playback_calls += 1
        self.process_entered.set()

        if self.process_gate is not None:
            self.process_gate.wait(timeout=3)

        if self.process_error is not None:
            raise self.process_error

    def track_listening(self, elapsed):
        self.track_listening_calls += 1

    def should_extend_queue(self):
        return self.extend_queue_needed

    def extend_queue(self):
        self.extend_queue_calls += 1

    def is_playing(self):
        return self.playing

    def refresh_session(self):
        self.refresh_session_calls += 1

    def save_session(self):
        self.save_session_calls += 1
        if self.save_session_error is not None:
            raise self.save_session_error

    def save_stats(self):
        self.save_stats_calls += 1


def wait_until(predicate, timeout=2.0):
    deadline = time.monotonic() + timeout

    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.01)

    return predicate()


def test_start_and_stop_manage_runtime_thread():
    playback = FakePlayback()
    runtime = PlaybackRuntime(playback)

    runtime.start()

    assert playback.process_entered.wait(timeout=1)
    assert runtime.is_alive()
    assert playback.ensure_ready_calls == 1

    runtime.stop()

    assert not runtime.is_alive()
    assert playback.refresh_session_calls == 1
    assert playback.save_session_calls == 1
    assert playback.save_stats_calls == 1


def test_start_does_not_create_a_duplicate_thread():
    gate = threading.Event()
    playback = FakePlayback(process_gate=gate)
    runtime = PlaybackRuntime(playback)

    runtime.start()
    assert playback.process_entered.wait(timeout=1)
    original_thread = runtime._thread

    runtime.start()

    assert runtime._thread is original_thread
    assert playback.ensure_ready_calls == 1

    gate.set()
    runtime.stop()



def test_runtime_executes_periodic_playback_maintenance(monkeypatch):
    monkeypatch.setattr(PlaybackRuntime, "STATS_SAMPLE_INTERVAL", 0.1)
    monkeypatch.setattr(PlaybackRuntime, "SESSION_SAVE_INTERVAL", 0.01)
    monkeypatch.setattr(PlaybackRuntime, "STATS_SAVE_INTERVAL", 0.01)

    playback = FakePlayback(
        extend_queue_needed=True,
        playing=True,
    )
    runtime = PlaybackRuntime(playback)

    runtime.start()

    assert wait_until(
        lambda: (
            playback.track_listening_calls >= 1
            and playback.extend_queue_calls >= 1
            and playback.refresh_session_calls >= 1
            and playback.save_session_calls >= 1
            and playback.save_stats_calls >= 1
        )
    )

    runtime.stop()

    assert playback.track_listening_calls >= 1
    assert playback.extend_queue_calls >= 1
    assert playback.refresh_session_calls >= 2
    assert playback.save_session_calls >= 2
    assert playback.save_stats_calls >= 2

def test_start_failure_does_not_leave_runtime_marked_as_running():
    playback = FakePlayback(
        ensure_error=RuntimeError("player initialization failed")
    )
    runtime = PlaybackRuntime(playback)

    with pytest.raises(RuntimeError, match="player initialization failed"):
        runtime.start()

    assert not runtime.is_alive()


def test_runtime_exception_stops_thread_and_attempts_final_persistence(
    monkeypatch,
    caplog,
):
    thread_errors = []
    monkeypatch.setattr(
        threading,
        "excepthook",
        lambda args: thread_errors.append(args.exc_value),
    )

    playback = FakePlayback(
        process_error=RuntimeError("simulated playback failure"),
        save_session_error=OSError("session storage unavailable"),
    )
    runtime = PlaybackRuntime(playback)

    runtime.start()
    assert playback.process_entered.wait(timeout=1)

    assert wait_until(lambda: not runtime.is_alive())

    assert playback.refresh_session_calls == 1
    assert playback.save_session_calls == 1
    assert playback.save_stats_calls == 1
    assert thread_errors
    assert isinstance(thread_errors[0], RuntimeError)
    assert "simulated playback failure" in caplog.text
    assert "Failed to save playback session" in caplog.text



def test_runtime_can_restart_after_previous_thread_failed(monkeypatch):
    thread_errors = []
    monkeypatch.setattr(
        threading,
        "excepthook",
        lambda args: thread_errors.append(args.exc_value),
    )

    playback = FakePlayback(
        process_error=RuntimeError("first run failed")
    )
    runtime = PlaybackRuntime(playback)

    runtime.start()
    assert playback.process_entered.wait(timeout=1)
    assert wait_until(lambda: not runtime.is_alive())

    playback.process_error = None
    runtime.start()

    assert wait_until(lambda: playback.process_playback_calls >= 2)
    assert runtime.is_alive()
    assert playback.ensure_ready_calls == 2

    runtime.stop()
    assert not runtime.is_alive()
    assert len(thread_errors) == 1

def test_runtime_cannot_restart_while_previous_thread_is_still_alive():
    gate = threading.Event()
    playback = FakePlayback(process_gate=gate)
    runtime = PlaybackRuntime(playback)

    runtime.start()
    assert playback.process_entered.wait(timeout=1)

    with pytest.raises(RuntimeError, match="não encerrou dentro do prazo"):
        runtime.stop(timeout=0.01)

    with pytest.raises(RuntimeError, match="still shutting down"):
        runtime.start()

    assert playback.ensure_ready_calls == 1

    gate.set()
    assert wait_until(lambda: not runtime.is_alive())
    runtime.stop()

    assert not runtime.is_alive()
