
import magic
from pathlib import Path

def is_video(file: str, use_mime: bool) -> bool:
    if use_mime == True:
        mime = magic.from_file(file, mime=True)
        return mime[:5] == "video"
    else:
        return Path(file).suffix[1:].lower() in ["mkv", "mp4", "avi", "mpg", "mpeg", "mov"]
