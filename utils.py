
import cchardet
import json
import logging
import magic
import os.path
import re
import subprocess
from collections import namedtuple
from pathlib import Path

Subtitle = namedtuple("Subtitle", "language")
VideoInfo = namedtuple("VideoInfo", "subtitles")
txt_format1 = re.compile("[0-9]{2}:[0-9]{2}:[0-9]{2}:.*")
txt_format2 = re.compile("\{[0-9]+\}\{[0-9]+\}.*")


def start_process(process: str, args: [str]):
    command = [process]
    command.extend(args)

    logging.debug(f"Starting {process} with options: {' '.join(args)}")
    status = subprocess.run(command, capture_output = True)
    logging.debug(f"Process finished with {status.returncode}")

    return status

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

def get_video_data(path: str) -> [VideoInfo]:
    args = []
    args.extend(["-v", "quiet"])
    args.extend(["-print_format", "json"])
    args.append("-show_format")
    args.append("-show_streams")
    args.append(path)

    process = start_process("ffprobe", args)

    output_lines = process.stdout
    output_str = output_lines.decode('utf8')
    output_json = json.loads(output_lines)

    subtitles = []
    for stream in output_json["streams"]:
        type = stream["codec_type"]
        if type == "subtitle":
            subtitles.append(Subtitle(stream["tags"]["language"]))

    return VideoInfo(subtitles)
