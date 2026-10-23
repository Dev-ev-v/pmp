import json
import socket


class MPVEventClient:

    def __init__(self, config):
        self._socket_path = config.socket_path
        self._sock = None
        self._buffer = b""

    @property
    def socket(self):
        return self._sock

    def connect(self):
        if self._sock is not None:
            return

        self._sock = socket.socket(
            socket.AF_UNIX,
            socket.SOCK_STREAM,
        )

        self._sock.connect(
            str(self._socket_path)
        )

        self._sock.setblocking(False)

    def observe_property(self, name):
        payload = {
            "command": [
                "observe_property",
                1,
                name,
            ]
        }

        self._sock.sendall(
            (json.dumps(payload) + "\n").encode()
        )
        
    def observe_event(self, name):
        payload = {
            "command": [
                "observe_event",
                name,
            ]
        }

        self._sock.sendall(
            (json.dumps(payload) + "\n").encode()
        )

    def read_events(self):
        events = []

        while True:
            try:
                chunk = self._sock.recv(4096)
            except BlockingIOError:
                break

            if not chunk:
                break

            self._buffer += chunk

        while b"\n" in self._buffer:
            line, self._buffer = self._buffer.split(
                b"\n",
                1,
            )

            if not line:
                continue

            message = json.loads(line.decode())
            
            if "event" not in message:
            	continue
            
            events.append(message)

        return events