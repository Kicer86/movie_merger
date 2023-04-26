
import inspect
import os
import shutil
import unittest


def prepare_temp_dir():
    tmp_dir = "_" + inspect.stack()[1].function
    if os.path.exists(tmp_dir):
        shutil.rmtree(tmp_dir)

    os.mkdir(tmp_dir)

    return tmp_dir


class SimpleSubtitlesMerge(unittest.TestCase):

    def test_dry_run_is_respected(self):
        td = prepare_temp_dir()

        for video in os.scandir("videos"):
            os.symlink(video, td + "/" + video.name)
        pass


if __name__ == '__main__':
    unittest.main()
