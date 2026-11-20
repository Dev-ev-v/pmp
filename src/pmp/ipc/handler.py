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
    	source_selection = args.get(
    		"source_selection",
    		None,
    	)
    	
    	track_ordering = args.get(
    		"track_ordering",
    		None,
    	)
    	
    	resume = args.get(
    		"resume",
    		False,
    	)
    	
    	self._playback.play(
    		target,
    		source_selection,
    		track_ordering,
    		resume,
    	)

    def handle(self, request):
        if not isinstance(request, dict):
            raise ValueError("Request must be a JSON object.")

        command = request.get("command")

        if not isinstance(command, str):
            raise ValueError("Request must contain a valid command.")

        args = request.get("args", {})

        if not isinstance(args, dict):
            raise ValueError("'args' must be a JSON object.")

        try:
            if command == "ping":
                return "pong"
                
            if command == "get_state":
            	state = self._playback.get_playback_state()
            	return serialize_state(state)
                
            if command == "source_selection":
            	enabled = self._playback.source_selection()
            	return str(enabled)
            
            if command == "track_ordering":
            	enabled = self._playback.track_ordering()
            	return str(enabled)
            	
            if command == "loop":
            	enabled = self._playback.loop()
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