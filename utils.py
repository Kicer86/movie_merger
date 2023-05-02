
import magic
import re
from pathlib import Path

txt_format1 = re.compile("[0-9]{2}:[0-9]{2}:[0-9]{2}:.*")
txt_format2 = re.compile("\{[0-9]+\}\{[0-9]+\}.*")


def is_video(file: str, use_mime: bool) -> bool:
    if use_mime == True:
        mime = magic.from_file(file, mime=True)
        return mime[:5] == "video"
    else:
        return Path(file).suffix[1:].lower() in ["mkv", "mp4", "avi", "mpg", "mpeg", "mov"]


def is_subtitle(file: str) -> bool:
    ext = file[-4:]

    if ext == ".srt":
        return True
    elif ext == ".txt":
        with open(file, 'r') as text_file:
            line = text_file.readline()

            if txt_format1.fullmatch(line) or txt_format2.fullmatch(line):
                return True

    return False
