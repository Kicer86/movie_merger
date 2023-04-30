
import sys
sys.path.append("..")

import hashlib
import inspect
import os
import shutil
import subprocess
import tempfile
import unittest

import utils
import twotone


def list_files(path: str) -> []:
    results = []

    for filename in os.listdir(path):
        filepath = os.path.join(path, filename)

        if os.path.isfile(filepath):
            results.append(filepath)

    return results


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


def file_tracks(path: str) -> ():
    tracks= {}

    process = subprocess.run(["mkvmerge", "-i", path], env={"LC_ALL": "C"}, capture_output=True)

    output_lines = process.stdout.splitlines()
    for output_line in output_lines:
        line = output_line.rstrip().decode("utf-8")
        if line[:8] == "Track ID":
            line_splited = line[9:].split(" ")
            id = line_splited[0]
            type = line_splited[1]
            details = " ".join(line_splited[2:])

            tracks.setdefault(type, []).append(details)

    return tracks


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


class SimpleSubtitlesMerge(unittest.TestCase):

    def test_dry_run_is_respected(self):
        with TestDataWorkingDirectory() as td:
            for video in os.scandir("videos"):
                if (utils.is_video(video.path, use_mime = False)):
                    os.symlink(os.path.join(os.getcwd(), video.path), os.path.join(td.path, video.name))

            for subtitle in os.scandir("subtitles"):
                os.symlink(os.path.join(os.getcwd(), subtitle.path), os.path.join(td.path, subtitle.name))

            hashes_before = hashes(td.path)
            self.assertEqual(len(hashes_before), 2 * 9)        # 9 videos and 9 subtitles expected
            twotone.run([td.path, "--dry-run"])
            hashes_after = hashes(td.path)

            self.assertEqual(hashes_before, hashes_after)

    def test_many_videos_conversion(self):
        with TestDataWorkingDirectory() as td:
            for video in os.scandir("videos"):
                if (utils.is_video(video.path, use_mime = False)):
                    os.symlink(os.path.join(os.getcwd(), video.path), os.path.join(td.path, video.name))

            for subtitle in os.scandir("subtitles"):
                os.symlink(os.path.join(os.getcwd(), subtitle.path), os.path.join(td.path, subtitle.name))

            files_before = list_files(td.path)
            self.assertEqual(len(files_before), 2 * 9)        # 9 videos and 9 subtitles expected

            twotone.run([td.path])

            files_after = list_files(td.path)
            self.assertEqual(len(files_after), 1 * 9)        # 9 mkv videos expected

            for video in files_after:
                self.assertEqual(video[-4:], ".mkv")
                tracks = file_tracks(video)
                self.assertEqual(len(tracks["video"]), 1)
                self.assertEqual(len(tracks["subtitles"]), 1)

    def test_appending_subtitles_to_mkv_with_subtitles(self):
        with TestDataWorkingDirectory() as td:

            # combine mp4 with srt into mkv
            os.symlink(os.path.join(os.getcwd(), "videos", "Atoms - 8579.mp4"),
                       os.path.join(td.path, "Atoms - 8579.mp4"))

            os.symlink(os.path.join(os.getcwd(), "subtitles", "Atoms - 8579.srt"),
                       os.path.join(td.path, "Atoms - 8579.srt"))

            twotone.run([td.path])

            # combine mkv with srt into mkv with 2 subtitles
            os.symlink(os.path.join(os.getcwd(), "subtitles", "Atoms - 8579.srt"),
                       os.path.join(td.path, "Atoms - 8579.srt"))

            twotone.run([td.path])

            # verify results
            files_after = list_files(td.path)
            self.assertEqual(len(files_after), 1)

            video = files_after[0]
            self.assertEqual(video[-4:], ".mkv")
            tracks = file_tracks(video)
            self.assertEqual(len(tracks["video"]), 1)
            self.assertEqual(len(tracks["subtitles"]), 2)


if __name__ == '__main__':
    unittest.main()
