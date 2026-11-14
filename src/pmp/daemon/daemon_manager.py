import os
import signal
import time
import socket
import subprocess
import sys
import time
from pathlib import Path

from pmp.ipc.server import HOST, PORT
from pmp.paths import paths
from pmp.config import Config

class DaemonManager:
    def __init__(self, config: Config):
        self._config = config
        self._pid_file = paths.daemon_pid

    def is_running(self):
        pid = self._read_pid()

        if pid is None:
            return False

        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            self._remove_pid()
            return False
        except PermissionError:
            return True

        return True

    def start(self):
        if self.is_running():
            return

        with paths.log.open("a") as log_file:
            subprocess.Popen(
            	[
            		sys.executable,
            		"-m",
            		"pmp.daemon",
            	],
            	start_new_session=True,
            	stdin=subprocess.DEVNULL,
            	stdout=log_file,
            	stderr=subprocess.STDOUT,
            )

        self._wait_until_ready()

    def ensure_running(self):
        if not self.is_running():
            self.start()

    def _wait_until_ready(self):
        timeout = 5
        start = time.monotonic()

        while time.monotonic() - start < timeout:
            try:
                with socket.create_connection(
                    (HOST, PORT),
                    timeout=0.2,
                ):
                    return

            except OSError:
                time.sleep(0.05)

        raise RuntimeError(
            "PMP daemon did not become ready."
        )

    def _read_pid(self):
        try:
            return int(self._pid_file.read_text())
        except (FileNotFoundError, ValueError):
            return None

    def _remove_pid(self):
        try:
            self._pid_file.unlink()
        except FileNotFoundError:
            pass
            
            
    def reset(self):
        """
        Encerra o daemon e a instância de mpv do PMP.
        Preserva os dados persistidos da aplicação.
        """
        targets = (
            (self._pid_file, self._is_daemon),
            (paths.mpv_pid, self._is_pmp_mpv),
        )

        errors = []

        for pid_file, validator in targets:
            pid = self._read_pid_file(pid_file)

            if pid is None:
                self._remove_pid_file(pid_file)
                continue

            if not validator(pid):
                # O processo já morreu ou o PID foi reutilizado.
                self._remove_pid_file(pid_file)
                continue

            try:
                self._terminate_process(pid, validator)
            except (OSError, RuntimeError) as exc:
                errors.append(f"PID {pid}: {exc}")
                continue

            self._remove_pid_file(pid_file)

        if errors:
            raise RuntimeError("; ".join(errors))

        self._remove_stale_socket()

    @staticmethod
    def _read_pid_file(pid_file):
        try:
            pid = int(pid_file.read_text().strip())
        except (FileNotFoundError, ValueError, OSError):
            return None

        return pid if pid > 1 else None

    @staticmethod
    def _read_cmdline(pid):
        try:
            raw = Path(f"/proc/{pid}/cmdline").read_bytes()
        except (FileNotFoundError, PermissionError, OSError):
            return None

        return [
            arg.decode(errors="replace")
            for arg in raw.split(b"\0")
            if arg
        ]

    @classmethod
    def _is_daemon(cls, pid):
        args = cls._read_cmdline(pid)
        return args is not None and (
            "-m" in args
            and "pmp.daemon" in args
        )

    def _is_pmp_mpv(self, pid):
        args = self._read_cmdline(pid)

        if args is None:
            return False

        # Identifica a instância pelo socket exclusivo do PMP.
        expected_socket = str(self._config.socket_path)

        return (
            any(Path(arg).name == "mpv" for arg in args)
            and any(
                arg == f"--input-ipc-server={expected_socket}"
                for arg in args
            )
        )

    @staticmethod
    def _terminate_process(pid, validator, timeout=2.0):
        if not validator(pid):
            return

        os.kill(pid, signal.SIGTERM)
        deadline = time.monotonic() + timeout

        while time.monotonic() < deadline:
            if not validator(pid):
                return
            time.sleep(0.05)

        # Nunca envia SIGKILL sem revalidar o PID.
        if validator(pid):
            os.kill(pid, signal.SIGKILL)

        deadline = time.monotonic() + timeout

        while time.monotonic() < deadline:
            if not validator(pid):
                return
            time.sleep(0.05)

        raise RuntimeError("Process did not terminate.")

    @staticmethod
    def _remove_pid_file(pid_file):
        try:
            pid_file.unlink()
        except FileNotFoundError:
            pass

    def _remove_stale_socket(self):
        socket_path = self._config.socket_path

        if not socket_path.exists():
            return

        # Não apaga um socket que ainda responde.
        import socket

        try:
            with socket.socket(
                socket.AF_UNIX,
                socket.SOCK_STREAM,
            ) as sock:
                sock.settimeout(0.2)
                sock.connect(str(socket_path))

            raise RuntimeError(
                "The MPV socket is still active; refusing to remove it."
            )

        except ConnectionRefusedError:
            socket_path.unlink(missing_ok=True)
        except FileNotFoundError:
            pass
        except TimeoutError as exc:
            raise RuntimeError(
                "Could not determine whether the MPV socket is stale."
            ) from exc
                                                