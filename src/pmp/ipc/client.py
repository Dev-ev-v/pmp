import json
import socket

from pmp.ipc.server import HOST, PORT


class IPCClient:
    def send(
        self,
        command: str,
        args: dict | None = None,
    ):
        request = {
            "command": command,
            "args": args or {},
        }

        payload = (
            json.dumps(request) + "\n"
        ).encode("utf-8")

        try:
            with socket.create_connection(
                (HOST, PORT),
                timeout=5,
            ) as sock:
                sock.sendall(payload)

                with sock.makefile("rb") as reader:
                    line = reader.readline()

        except TimeoutError as exc:
            raise ConnectionError(
                "IPC server timed out. "
                "It may be unresponsive or have been terminated."
            ) from exc

        except (
            ConnectionRefusedError,
            ConnectionResetError,
            BrokenPipeError,
        ) as exc:
            raise ConnectionError(
                "IPC server is unavailable or the connection was lost."
            ) from exc

        if not line:
            raise ConnectionError(
                "IPC server closed the connection without responding."
            )

        try:
            response = json.loads(line.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise ConnectionError(
                "IPC server returned an invalid response."
            ) from exc

        if not response.get("ok"):
            raise RuntimeError(
                response.get("error", "Unknown IPC error.")
            )

        return response.get("result")