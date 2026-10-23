import subprocess
import time
import socket
from pathlib import Path

from pmp.config import Config
from pmp.paths import paths


class MPVProcess:

    def __init__(self, config: Config):
        self._config = config
        self._process: subprocess.Popen | None = None


    def running(self) -> bool:
        
        if not self._config.socket_path.exists():
        	return False
        
        try:
            with socket.socket(
            	socket.AF_UNIX,
            	socket.SOCK_STREAM,
            ) as sock:
            	
            	sock.settimeout(0.5)
            	
            	sock.connect(
            		str(self._config.socket_path)
            	)
            	
            	return True
        
        except OSError:
        	return False


    def start(self):
        if self.running():
        	return
        
        if self._config.socket_path.exists():
        	self._config.socket_path.unlink()
        
        self._process = subprocess.Popen( [
            self._config.mpv_binary,
            "--idle=yes",
            f"--input-ipc-server={self._config.socket_path}",
        ],
        	stdout=subprocess.DEVNULL,  
            stderr=subprocess.DEVNULL,  
        )
        paths.mpv_pid.write_text(str(self._process.pid))
        self._wait_socket()

    def terminate(self, timeout: float = 2.0):
        process = self._process

        if process is not None and process.poll() is None:
            process.terminate()

            try:
                process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=timeout)

        self._process = None

        # O socket pode ter ficado para trás após uma falha.
        if self._config.socket_path.exists():
            try:
                self._config.socket_path.unlink()
            except FileNotFoundError:
                pass
                
        try:
        	paths.mpv_pid.unlink()
        except FileNotFoundError:
        	pass
    
    def _wait_socket(self) -> None:
    	timeout = 5
    	start = time.time()
    	
    	while not self.running():
    		if self._process is not None:
    			returncode = self._process.poll()
    			
    			if returncode is not None:
    				raise RuntimeError(
    					f"mpv encerrou durante a inicialização "
    					f"(exit code {returncode})"
    				)
    		
    		if time.time() - start > timeout:
    			raise RuntimeError(
    				"mpv não criou o socket IPC"
    			)
    		
    		time.sleep(0.05)