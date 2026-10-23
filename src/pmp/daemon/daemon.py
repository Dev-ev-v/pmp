import os
import time
import threading
from pathlib import Path

from pmp.container import container
from pmp.ipc.handler import CommandHandler
from pmp.ipc.server import IPCServer


class PMPDaemon:
    def __init__(self, pid_file):
        self._pid_file = pid_file
        self.container = container
        
        self.handler = CommandHandler(
        	self.container.playback
        )
        self.ipc = IPCServer(
        	self.handler
        )

    def run(self):
    	self._write_pid()
    	
    	try:
    		self.container.runtime.start()
    		
    		ipc_thread = threading.Thread(
    			target=self.ipc.run,
    			daemon=True,
    		)
    		ipc_thread.start()
    		
    		while True:
    			time.sleep(1)
    	
    	finally:
    	   self.container.runtime.stop()
    	   self._remove_pid()

    def _write_pid(self):
        self._pid_file.write_text(str(os.getpid()))

    def _remove_pid(self):
        try:
            self._pid_file.unlink()
        except FileNotFoundError:
            pass