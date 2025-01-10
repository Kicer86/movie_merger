
import os
import shutil
import unittest
from typing import List

import twotone.twotone as twotone
from twotone.tools.transcode import Transcoder
from twotone.tools.utils import split_path
from common import TestDataWorkingDirectory, add_test_media, list_files


class ConcatenateTests(unittest.TestCase):

    def _create_media(self, wd: str, base_file: str, partnames: List[str]):
        media_file_components = split_path(base_file)

        def build_part(part: str) -> str:
            return os.path.join(wd, media_file_components[1]) + part + "." + media_file_components[2]

        for partname in partnames:
            target = build_part(partname)
            shutil.copy2(base_file, target)


    def _setup_valid_media(self, wd: str):
        media_files = add_test_media("Frog.*mp4", wd)

        wdX = [os.path.join(wd, str(i)) for i in range(5)]

        for wdx in wdX:
            os.makedirs(wdx)

        self.assertEqual(len(media_files), 1)
        media_file = media_files[0]

        self._create_media(wdX[0], media_file, [" CD1", " CD2"])
        self._create_media(wdX[1], media_file, ["-CD1", "-CD2", "-CD3", "-CD4"])
        self._create_media(wdX[2], media_file, [".CD1", ".CD2", ".CD3", ".CD4", ".CD5", ".CD6", ".CD7"])
        self._create_media(wdX[3], media_file, [" cd1", " cd2", " cd3", " cd4", " cd5", " cd6", " cd7", " cd8", " cd9", " cd10", " cd11", " cd12", ])
        self._create_media(wdX[4], media_file, [" Cd01", " Cd02", " Cd03", " Cd04", " Cd05", " Cd06", " Cd07", " Cd08", " Cd09", " Cd010", " Cd11", " Cd12"])


    def test_dry_run_is_respected(self):
        with TestDataWorkingDirectory() as td:
            self._setup_valid_media(td.path)

            files_before = list_files(td.path)
            twotone.execute(["concatenate", td.path])

            files_after = list_files(td.path)
            self.assertEqual(files_after, files_before)


if __name__ == '__main__':
    unittest.main()
