
import cchardet
import magic
import os.path
import re
from pathlib import Path

txt_format1 = re.compile("[0-9]{2}:[0-9]{2}:[0-9]{2}:.*")
txt_format2 = re.compile("\{[0-9]+\}\{[0-9]+\}.*")


def file_encoding(file: str) -> str:
    detector = cchardet.UniversalDetector()

    with open(file, 'rb') as file:
        for line in file.readlines():
            detector.feed(line)
            if detector.done:
                break
        detector.close()

    encoding = detector.result["encoding"]

    if encoding == "UTF-8-SIG":
        encoding = "UTF-8"

    return encoding


def is_video(file: str) -> bool:
    return Path(file).suffix[1:].lower() in ["mkv", "mp4", "avi", "mpg", "mpeg", "mov"]


def is_subtitle(file: str) -> bool:
    ext = file[-4:]

    if ext == ".srt" or ext == ".sub" or ext == ".txt":
        file = os.path.realpath(file)
        mime = magic.from_file(file, mime=True)

        if mime == "application/x-subrip":
            return True

        encoding = file_encoding(file)

        with open(file, 'r', encoding = encoding) as text_file:
            line = text_file.readline().rstrip()

            if txt_format1.fullmatch(line) or txt_format2.fullmatch(line):
                return True

    return False
