
import json
import socket
import traceback

HOST = "127.0.0.1"
PORT = 8765


class IPCServer:
    def __init__(self, handler):
        self._handler = handler

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

    def run(self):
        while True:
            connection, _ = self._socket.accept()

            with connection:
                try:
                    with connection.makefile("rb") as reader:
                        line = reader.readline()

                    if not line:
                        continue

                    request = json.loads(line.decode("utf-8"))
                    result = self._handler.handle(request)

                    response = {
                        "ok": True,
                        "result": result,
                    }

                except Exception as exc:
                    response = {
                        "ok": False,
                        "error": str(exc),
                        "exception_type": type(exc).__name__,
                        "traceback": traceback.format_exc(),
                    }

                payload = (
                    json.dumps(response) + "\n"
                ).encode("utf-8")

                connection.sendall(payload)
