
import json
import logging
import socket
import threading

HOST = "127.0.0.1"
PORT = 8765

MAX_REQUEST_SIZE = 1024 * 1024
CONNECTION_TIMEOUT = 5.0
SERVER_TIMEOUT = 0.5

logger = logging.getLogger(__name__)


class IPCServer:
    def __init__(self, handler):
        self._handler = handler
        self._stop_event = threading.Event()
        self._close_lock = threading.Lock()
        self._closed = False

        self._socket = socket.socket(
            socket.AF_INET,
            socket.SOCK_STREAM,
        )

        self._socket.setsockopt(
            socket.SOL_SOCKET,
            socket.SO_REUSEADDR,
            1,
        )

        self._socket.bind((HOST, PORT))
        self._socket.listen(5)
        self._socket.settimeout(SERVER_TIMEOUT)

    @staticmethod
    def _error_response(exc):
        return {
            "ok": False,
            "error": str(exc),
            "exception_type": type(exc).__name__,
        }

    @staticmethod
    def _serialize_response(response):
        try:
            return (
                json.dumps(response) + "\n"
            ).encode("utf-8")

        except (TypeError, ValueError):
            logger.exception(
                "Could not serialize IPC response."
            )

            fallback = {
                "ok": False,
                "error": "Internal response serialization error.",
                "exception_type": "SerializationError",
            }

            return (
                json.dumps(fallback) + "\n"
            ).encode("utf-8")

    def _handle_connection(self, connection):
        try:
            with connection:
                connection.settimeout(CONNECTION_TIMEOUT)

                with connection.makefile("rb") as reader:
                    line = reader.readline(
                        MAX_REQUEST_SIZE + 1
                    )

                if not line:
                    return

                if len(line) > MAX_REQUEST_SIZE:
                    response = {
                        "ok": False,
                        "error": "Request too large.",
                        "exception_type": "RequestTooLarge",
                    }
                else:
                    try:
                        request = json.loads(
                            line.decode("utf-8")
                        )

                        result = self._handler.handle(request)

                        response = {
                            "ok": True,
                            "result": result,
                        }

                    except Exception as exc:
                        logger.exception(
                            "Error while handling IPC request."
                        )
                        response = self._error_response(exc)

                payload = self._serialize_response(response)
                connection.sendall(payload)

        except (
            BrokenPipeError,
            ConnectionResetError,
            ConnectionAbortedError,
            TimeoutError,
            OSError,
        ):
            logger.debug(
                "IPC connection closed or timed out.",
                exc_info=True,
            )

    def run(self):
        try:
            while not self._stop_event.is_set():
                try:
                    connection, _ = self._socket.accept()

                except socket.timeout:
                    continue

                except OSError:
                    if self._stop_event.is_set():
                        break

                    raise

                self._handle_connection(connection)

        finally:
            self.close()

    def close(self):
        self._stop_event.set()

        with self._close_lock:
            if self._closed:
                return

            self._closed = True

            try:
                self._socket.close()
            except OSError:
                logger.debug(
                    "Error while closing IPC socket.",
                    exc_info=True,
                )
