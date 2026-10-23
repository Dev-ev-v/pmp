import json
import socket

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
                    reader = connection.makefile("rb")
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
                    }

                payload = (
                    json.dumps(response) + "\n"
                ).encode("utf-8")

                connection.sendall(payload)
