
import logging
import os
import signal
import threading

from pmp.container import container
from pmp.ipc.handler import CommandHandler
from pmp.ipc.server import IPCServer

logger = logging.getLogger(__name__)


class PMPDaemon:

    def __init__(self, pid_file):
        self._pid_file = pid_file
        self.container = container

        self.handler = CommandHandler(
            self.container.playback
        )

        self.ipc = IPCServer(self.handler)

        self._stop_event = threading.Event()

    def _handle_signal(self, signum, frame):
        logger.info(
            "Received signal %s. Shutting down.",
            signum,
        )
        self._stop_event.set()

    def _install_signal_handlers(self):
        if threading.current_thread() is not threading.main_thread():
            return {}

        previous_handlers = {}

        for sig in (signal.SIGTERM, signal.SIGINT):
            previous_handlers[sig] = signal.getsignal(sig)
            signal.signal(sig, self._handle_signal)

        return previous_handlers

    @staticmethod
    def _restore_signal_handlers(handlers):
        for sig, previous in handlers.items():
            signal.signal(sig, previous)

    def run(self):
        ipc_thread = None
        previous_handlers = {}
        pid_written = False

        self._stop_event.clear()

        try:
            previous_handlers = self._install_signal_handlers()

            self._write_pid()
            pid_written = True

            self.container.runtime.start()

            ipc_thread = threading.Thread(
                target=self.ipc.run,
                name="PMP-IPC",
                daemon=True,
            )

            ipc_thread.start()

            while not self._stop_event.wait(0.5):
                if not ipc_thread.is_alive():
                    raise RuntimeError(
                        "IPC server thread terminated unexpectedly."
                    )

                if not self.container.runtime.is_alive():
                    raise RuntimeError(
                        "Playback runtime thread terminated unexpectedly."
                    )

        finally:
            self._stop_event.set()

            try:
                self.ipc.close()
            except Exception:
                logger.exception(
                    "Failed to close IPC server."
                )

            if ipc_thread is not None:
                ipc_thread.join(timeout=2.0)

                if ipc_thread.is_alive():
                    logger.error(
                        "IPC thread did not terminate within timeout."
                    )

            try:
                self.container.runtime.stop()
            except Exception:
                logger.exception(
                    "Failed to stop playback runtime."
                )

            finally:
                if pid_written:
                    self._remove_pid()

                self._restore_signal_handlers(
                    previous_handlers
                )

    def _write_pid(self):
        self._pid_file.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self._pid_file.write_text(str(os.getpid()))

    def _remove_pid(self):
        try:
            self._pid_file.unlink()
        except FileNotFoundError:
            pass
