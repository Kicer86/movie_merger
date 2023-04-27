
import sys
sys.path.append("..")

import hashlib
import inspect
import os
import shutil
import unittest

import utils
import twotone


def hashes(path: str) -> [()]:
    results = []

    for filename in os.listdir(path):
        filepath = os.path.join(path, filename)

        if os.path.isfile(filepath):
            with open(filepath, "rb") as f:
                file_hash = hashlib.md5()
                while chunk := f.read(8192):
                    file_hash.update(chunk)

                results.append((filename, file_hash.hexdigest()))

    return results


class TestDataWorkingDirectory:
    def __init__(self):
        self.directory = None

    @property
    def path(self):
        return self.directory

    def __enter__(self):
        self.directory = "_" + inspect.stack()[1].function
        if os.path.exists(self.directory):
            shutil.rmtree(self.directory)

        os.mkdir(self.directory)
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
            self.assertTrue(len(hashes_before) == 2 * 9)        # 9 videos and 9 subtitles expected
            twotone.run([td.path, "--dry-run"])
            hashes_after = hashes(td.path)

            self.assertEqual(hashes_before, hashes_after)


if __name__ == '__main__':
    unittest.main()
