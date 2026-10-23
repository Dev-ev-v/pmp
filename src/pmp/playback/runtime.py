import threading
import time


class PlaybackRuntime:
    STATS_SAMPLE_INTERVAL = 0.2
    SESSION_SAVE_INTERVAL = 5.0
    STATS_SAVE_INTERVAL = 5.0

    def __init__(self, playback):
        self._playback = playback
        self._running = False
        self._thread = None    

    def start(self):
        if self._running:
            return

        self._playback.ensure_ready()
        self._running = True

        self._thread = threading.Thread(
            target=self._run,
            daemon=True,
        )
        self._thread.start()

    def is_alive(self):
        return (
            self._thread is not None
            and self._thread.is_alive()
        )

    def stop(self, timeout: float = 3.0):
        self._running = False

        thread = self._thread
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout)

        if thread is not None and thread.is_alive():
            raise RuntimeError(
                "PlaybackRuntime não encerrou dentro do prazo."
            )

        self._thread = None

    def _run(self):
        last_sample = time.monotonic()
        last_session_save = last_sample
        last_stats_save = last_sample

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

        self._playback.refresh_session()
        self._playback.save_session()
        self._playback.save_stats()
