
import sys
sys.path.append("..")

import hashlib
import subprocess
import unittest

import utils
import twotone
from common import TestDataWorkingDirectory, file_tracks, list_files, add_test_media


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


class SimpleSubtitlesMerge(unittest.TestCase):

    def test_dry_run_is_respected(self):
        with TestDataWorkingDirectory() as td:
            add_test_media(".*mp4|.*mov|.*srt", td.path)

            hashes_before = hashes(td.path)
            self.assertEqual(len(hashes_before), 2 * 9)        # 9 videos and 9 subtitles expected
            twotone.run([td.path, "--dry-run"])
            hashes_after = hashes(td.path)

            self.assertEqual(hashes_before, hashes_after)

    def test_many_videos_conversion(self):
        with TestDataWorkingDirectory() as td:
            add_test_media(".*mp4|.*mov|.*srt", td.path)

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
            add_test_media("Atoms.*(mp4|srt)", td.path)

            twotone.run([td.path])

            # combine mkv with srt into mkv with 2 subtitles
            add_test_media("Atoms.*srt", td.path)

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
            add_test_media("Atoms.*(mp4|srt)", td.path)

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
            add_test_media("Atoms.*mp4", td.path)
            add_test_media("Atoms.*srt", td.path, ["PL", "EN", "DE"])

            twotone.run([td.path])

            # verify results: all subtitle-like files should be sucked in
            files_after = list_files(td.path)
            self.assertEqual(len(files_after), 1)

            video = files_after[0]
            self.assertEqual(video[-4:], ".mkv")
            tracks = file_tracks(video)
            self.assertEqual(len(tracks["video"]), 1)
            self.assertEqual(len(tracks["subtitles"]), 3)

    def test_raw_txt_subtitles_are_ignored(self):
        # mkvmerge does not allow txt files with subtitles to be merged
        with TestDataWorkingDirectory() as td:
            add_test_media("herd-of-horses-in-fog.*(mp4|txt)", td.path)

            #expect nothing to be changed
            hashes_before = hashes(td.path)
            self.assertEqual(len(hashes_before), 2)
            twotone.run([td.path, "--disable-txt"])
            hashes_after = hashes(td.path)

            self.assertEqual(hashes_before, hashes_after)

    def test_raw_txt_subtitles_conversion(self):
        # Allow automatic txt to srt conversion
        with TestDataWorkingDirectory() as td:
            add_test_media("herd-of-horses-in-fog.*(mp4|txt)", td.path)

            twotone.run([td.path])

            # verify results
            files_after = list_files(td.path)
            self.assertEqual(len(files_after), 1)

            video = files_after[0]
            self.assertEqual(video[-4:], ".mkv")
            tracks = file_tracks(video)
            self.assertEqual(len(tracks["video"]), 1)
            self.assertEqual(len(tracks["subtitles"]), 1)


if __name__ == '__main__':
    unittest.main()
