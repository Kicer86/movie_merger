
import inspect
import json
import os
import shutil
import subprocess
import tempfile


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


def file_tracks(path: str) -> ():
    tracks= {}

    process = subprocess.run(["mkvmerge", "-J", path], env={"LC_ALL": "C"}, capture_output=True)

    output_lines = process.stdout
    output_str = output_lines.decode('utf8')
    output_json = json.loads(output_lines)

    for track in output_json["tracks"]:
        type = track["type"]
        tracks.setdefault(type, []).append(track)

    return tracks


def list_files(path: str) -> []:
    results = []

    for filename in os.listdir(path):
        filepath = os.path.join(path, filename)

        if os.path.isfile(filepath):
            results.append(filepath)

    return results
