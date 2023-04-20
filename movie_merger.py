
import magic
import os
import sys
from pathlib import Path


def simple_subtitle_search(path: str) -> [str]:
    video_name = Path(path).stem
    video_extension = Path(path).suffix
    dir = Path(path).parent

    subtitles = []

    for subtitle_ext in ["txt", "srt"]:
        subtitle_file = video_name + "." + subtitle_ext
        subtitle_path = os.path.join(dir, subtitle_file)
        if os.path.exists(subtitle_file):
            subtitles.append(subtitle_file)

    return subtitles


def aggressive_subtitle_search(path: str):
    simple_subtitle_search(path)
    pass


def is_video(file: str):
    mime = magic.from_file(file, mime=True)
    return mime[:5] == "video"


def process_dir(path: str):
    video_files = []
    for entry in os.scandir(path):
        if entry.is_file() and is_video(entry.path):
            video_files.append(entry.path)
        elif entry.is_dir():
            process_dir(entry.path)

    if len(video_files) == 1:
        aggressive_subtitle_search(video_files[0])
    if len(video_files) > 1:
        for video_file in video_files:
            simple_subtitle_search(video_file)


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Provide path to scan")
        exit(1)

    process_dir(sys.argv[1])
