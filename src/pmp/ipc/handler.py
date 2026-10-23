from dataclasses import asdict
from pathlib import Path
import json


def serialize_state(state):
    data = asdict(state)

    if data["path"] is not None:
        data["path"] = str(data["path"])

    data["queue"] = [
        {
            **song,
            "path": str(song["path"])
            if song["path"] is not None
            else None,
        }
        for song in data["queue"]
    ]

    return data


class CommandHandler:
    def __init__(self, playback):
        self._playback = playback
        
    def _play(self, args):
    	target = args.get("target")
    	shuffle = args.get(
    		"shuffle",
    		None,
    	)
    	
    	global_shuffle = args.get(
    		"global_shuffle",
    		None,
    	)
    	
    	resume = args.get(
    		"resume",
    		False,
    	)
    	
    	self._playback.play(
    		target,
    		shuffle,
    		global_shuffle,
    		resume,
    	)

    def handle(self, request):
        command = request["command"]
        args = request.get("args", {})

        try:
                
            if command == "get_state":
            	state = self._playback.get_playback_state()
            	return serialize_state(state)
                
            if command == "shuffle":
            	enabled = self._playback.shuffle()
            	return str(enabled)
            
            if command == "global_shuffle":
            	enabled = self._playback.global_shuffle()
            	return str(enabled)

            if command == "pause":
                self._playback.pause()
                return "ok"

            if command == "stop":
                self._playback.stop()
                return "ok"

            if command == "next":
                self._playback.next()
                return "ok"

            if command == "previous":
                self._playback.previous()
                return "ok"
                
            if command == "play":
            	self._play(
            		args
            	)
            	return "ok"

            return "unknown command"

        except Exception:
            raise