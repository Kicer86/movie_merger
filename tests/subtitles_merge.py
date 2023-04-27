
import sys
sys.path.append("..")

import inspect
import os
import shutil
import unittest

import utils


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
                    os.symlink(video, td.path + "/" + video.name)

            for subtitle in os.scandir("subtitles"):
                os.symlink(video, td.path + "/" + subtitle.name)


if __name__ == '__main__':
    unittest.main()
