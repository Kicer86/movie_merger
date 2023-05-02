
import sys
sys.path.append("..")

import hashlib
import json
import os
import subprocess
import unittest

import utils
import twotone
from common import TestDataWorkingDirectory


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

    process = subprocess.run(["mkvmerge", "-J", path], env={"LC_ALL": "C"}, capture_output=True)

    output_lines = process.stdout
    output_str = output_lines.decode('utf8')
    output_json = json.loads(output_lines)

    for track in output_json["tracks"]:
        type = track["type"]
        tracks.setdefault(type, []).append(track)

    return tracks


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

    def test_subtitles_language(self):
        with TestDataWorkingDirectory() as td:

            # combine mp4 with srt into mkv
            os.symlink(os.path.join(os.getcwd(), "videos", "Atoms - 8579.mp4"),
                       os.path.join(td.path, "Atoms - 8579.mp4"))

            os.symlink(os.path.join(os.getcwd(), "subtitles", "Atoms - 8579.srt"),
                       os.path.join(td.path, "Atoms - 8579.srt"))

            twotone.run([td.path, "-l", "pol"])

            # verify results
            files_after = list_files(td.path)
            self.assertEqual(len(files_after), 1)

            video = files_after[0]
            self.assertEqual(video[-4:], ".mkv")
            tracks = file_tracks(video)
            self.assertEqual(len(tracks["video"]), 1)
            self.assertEqual(len(tracks["subtitles"]), 1)
            self.assertEqual(tracks["subtitles"][0]["properties"]["language"], "pol")

    def test_multiple_subtitles_for_single_file(self):
        with TestDataWorkingDirectory() as td:

            # one file in directory with many subtitles
            os.symlink(os.path.join(os.getcwd(), "videos", "herd-of-horses-in-fog-13642605.mp4"),
                       os.path.join(td.path, "herd-of-horses-in-fog-13642605.mp4"))

            os.symlink(os.path.join(os.getcwd(), "subtitles", "herd-of-horses-in-fog-13642605.srt"),
                       os.path.join(td.path, "herd-of-horses-in-fog-13642605-EN.srt"))

            os.symlink(os.path.join(os.getcwd(), "subtitles", "herd-of-horses-in-fog-13642605.srt"),
                       os.path.join(td.path, "herd-of-horses-in-fog-13642605-DE.srt"))

            os.symlink(os.path.join(os.getcwd(), "subtitles", "herd-of-horses-in-fog-13642605.srt"),
                       os.path.join(td.path, "herd-of-horses-in-fog-13642605-PL.srt"))

            twotone.run([td.path])

            # verify results: all subtitle-like files should be sucked in
            files_after = list_files(td.path)
            self.assertEqual(len(files_after), 1)

            video = files_after[0]
            self.assertEqual(video[-4:], ".mkv")
            tracks = file_tracks(video)
            self.assertEqual(len(tracks["video"]), 1)
            self.assertEqual(len(tracks["subtitles"]), 3)


if __name__ == '__main__':
    unittest.main()
