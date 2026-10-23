import json
import socket

from pmp.config import Config
from pmp.player.exceptions import (
    MPVCommandError,
    MPVConnectionError,
)


class MPVClient:

    def __init__(
        self,
        config: Config,
    ):
        self._socket_path = config.socket_path


    def property(self, name: str):
        response = self.command(
            "get_property",
            name,
        )

        return response["data"]
        
    
    def command(
        self,
        *command,
    ) -> dict:

        payload = {
            "command": list(command)
        }

        message = (
            json.dumps(payload)
            + "\n"
        )


        try:

            with socket.socket(
                socket.AF_UNIX,
                socket.SOCK_STREAM,
            ) as sock:

                sock.settimeout(5)

                sock.connect(
                    str(self._socket_path)
                )

                sock.sendall(
                    message.encode()
                )

                response = self._receive(
                    sock
                )                


        except OSError as error:

            raise MPVConnectionError(
                "Falha na comunicação com mpv"
            ) from error
        
        if response.get("error") != "success":

            raise MPVCommandError(
                response
            )


        return response



    def _receive(
   	 self,
    	sock: socket.socket,
	) -> dict:

   	 buffer = b""
   	 
   	 while True:
   	 	chunk = sock.recv(4096)
   	 	
   	 	if not chunk:
   	 		raise MPVConnectionError(
   	 			"mpv fechou a conexão"
   	 		)
   	 	
   	 	buffer += chunk
   	 	
   	 	while b"\n" in buffer:
   	 		line, buffer = buffer.split(
   	 			b"\n",
   	 			1,
   	 		)
   	 		
   	 		if not line:
   	 			continue
   	 		
   	 		message = json.loads(
   	 			line.decode()
   	 		)
   	 		
   	 		if "request_id" in message:
   	 			return message