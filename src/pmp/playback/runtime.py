import logging
import threading
import time


logger = logging.getLogger(__name__)


class PlaybackRuntime:
    STATS_SAMPLE_INTERVAL = 0.2
    SESSION_SAVE_INTERVAL = 5.0
    STATS_SAVE_INTERVAL = 5.0

    def __init__(self, playback):
        self._playback = playback
        self._running = False
        self._thread = None
        self._lock = threading.Lock()

    def start(self):
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                if self._running:
                    return

                raise RuntimeError(
                    "PlaybackRuntime is still shutting down."
                )

            self._playback.ensure_ready()
            self._running = True

            self._thread = threading.Thread(
                target=self._run,
                name="PMP-PlaybackRuntime",
                daemon=True,
            )

            try:
                self._thread.start()
            except Exception:
                self._running = False
                self._thread = None
                raise

    def is_alive(self):
        thread = self._thread

        return (
            thread is not None
            and thread.is_alive()
        )

    def stop(self, timeout: float = 3.0):
        with self._lock:
            self._running = False
            thread = self._thread

        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout)

        if thread is not None and thread.is_alive():
            raise RuntimeError(
                "PlaybackRuntime não encerrou dentro do prazo."
            )

        with self._lock:
            if self._thread is thread:
                self._thread = None

    def _run(self):
        last_sample = time.monotonic()
        last_session_save = last_sample
        last_stats_save = last_sample

        try:
            while self._running:
                self._playback.process_playback()

                now = time.monotonic()

                if now - last_sample >= self.STATS_SAMPLE_INTERVAL:
                    elapsed = now - last_sample
                    last_sample = now

                    if elapsed <= self.STATS_SAMPLE_INTERVAL * 2:
                        self._playback.track_listening(elapsed)

                if self._playback.should_extend_queue():
                    self._playback.extend_queue()

                if now - last_session_save >= self.SESSION_SAVE_INTERVAL:
                    if self._playback.is_playing():
                        self._playback.refresh_session()
                        self._playback.save_session()
                        last_session_save = now

                if now - last_stats_save >= self.STATS_SAVE_INTERVAL:
                    self._playback.save_stats()
                    last_stats_save = now

                time.sleep(0.05)

        except Exception:
            logger.exception(
                "PlaybackRuntime terminated unexpectedly."
            )
            raise

        finally:
            self._save_final_state()

            with self._lock:
                self._running = False

    def _save_final_state(self):
        operations = (
            ("refresh playback session", self._playback.refresh_session),
            ("save playback session", self._playback.save_session),
            ("save playback stats", self._playback.save_stats),
        )

        for description, operation in operations:
            try:
                operation()
            except Exception:
                logger.exception(
                    "Failed to %s during runtime shutdown.",
                    description,
                )
