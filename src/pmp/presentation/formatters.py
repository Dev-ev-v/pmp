def format_duration(seconds: float) -> str:
    seconds = int(seconds)
    	
    intervals = [
    	("d", 86400),
    	("h", 3600),
    	("m", 60),
    	("s", 1),
    ]
    parts = []
    	
    for suffix, unit in intervals:
    	value = seconds // unit
    		
    	if value:
    		seconds %= unit
    		parts.append(f"{value}{suffix}")
    		
    	if len(parts) == 2:
    			break
    	
    return " ".join(parts) or "0s"

def format_time(seconds: float) -> str:
    seconds = int(seconds)

    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)

    if hours:
        return f"{hours}:{minutes:02}:{seconds:02}"

    return f"{minutes:02}:{seconds:02}"


def progress_bar(position: float, duration: float, width: int = 24) -> str:
    if duration <= 0:
        return "─" * width

    ratio = min(max(position / duration, 0), 1)

    cursor = int(ratio * (width - 1))

    return "".join(
        "●" if i == cursor else "━" if i < cursor else "─"
        for i in range(width)
    )