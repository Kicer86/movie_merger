
import hashlib
import inspect
import json
import os
import re
import shutil
import subprocess
import tempfile

from pathlib import Path

current_path = os.path.dirname(os.path.abspath(__file__))


class TestDataWorkingDirectory:
    def __init__(self):
        self.directory = None

    @property
    def path(self):
        return self.directory

    def __enter__(self):
        self.directory = os.path.join(tempfile.gettempdir(), "twotone_tests", inspect.stack()[1].function)
        if os.path.exists(self.directory):
            shutil.rmtree(self.directory)

        os.makedirs(self.directory, exist_ok=True)
        return self

    def __exit__(self, type, value, traceback):
        shutil.rmtree(self.directory)


def list_files(path: str) -> []:
    results = []

    for root, _, files in os.walk(path):
        for filename in files:
            filepath = os.path.join(root, filename)

            if os.path.isfile(filepath):
                results.append(filepath)

    return results


def add_test_media(filter: str, test_case_path: str, suffixes: [str] = [None]):
    filter_regex = re.compile(filter)

    for media in ["subtitles", "subtitles_txt", "videos"]:
        with os.scandir(os.path.join(current_path, media)) as it:
            for file in it:
                file_path = file.name
                if filter_regex.fullmatch(file_path):
                    for suffix in suffixes:
                        suffix = "" if suffix is None else "-" + suffix + "-"
                        file_path = Path(file)
                        dst_file_name = file_path.stem + suffix + file_path.suffix
                        os.symlink(os.path.join(current_path, media, file_path),
                                os.path.join(test_case_path, dst_file_name))


def get_video(name: str) -> str:
    return os.path.join(current_path, "videos", name)


def hashes(path: str) -> [()]:
    results = []

    files = list_files(path)

    for filepath in files:
        with open(filepath, "rb") as f:
            file_hash = hashlib.md5()
            while chunk := f.read(8192):
                file_hash.update(chunk)

            results.append((filepath, file_hash.hexdigest()))

    return results


def generate_microdvd_subtitles(path: str, length: int, fps: float = 60):
    with open(path, "w") as sf:
        b = 0
        e = 0
        for t in range(length):
            b = int(round(t * fps, 0))
            e = int(round(b + fps/2, 0))
            sf.write(f"{{{b}}}{{{e}}}{t}\n")

        # microdvd requires at least 3 entries for ffmpeg to consume it
        if length < 3:
            # add some empty entries to satisfy ffmpeg
            sf.write(f"{{{e}}}{{{e + 1}}}\n")
            sf.write(f"{{{e + 1}}}{{{e + 2}}}\n")
