
import os
import unittest

import utils
import pooch
from common import TestDataWorkingDirectory


video_cache = pooch.create(
    path=pooch.os_cache("twotone_test_data"),
    base_url="https://www.sample-videos.com/",
    registry={
        "video321/mp4/720/big_buck_bunny_720p_2mb.mp4":  "md5:6cff9004d995b5c929ce90e391100996",
        "video321/mp4/720/big_buck_bunny_720p_10mb.mp4": "md5:798ce2689035bc7ed07c1f9bf75f754c",
    },
)


class UtilsTests(unittest.TestCase):

    def _test_content(self, content: str, valid: bool):
        with TestDataWorkingDirectory() as wd:
            subtitle_path = os.path.join(wd.path, "subtitle.txt")

            with open(subtitle_path, 'w') as subtitle_file:
                subtitle_file.write(content)

            if valid:
                self.assertTrue(utils.is_subtitle(subtitle_path))
            else:
                self.assertFalse(utils.is_subtitle(subtitle_path))

    def _test_conversion(self, wd: str, file: str, needs_conversion: bool):
        full_path = os.path.join(wd, file)
        self.assertEqual(utils.is_subtitle_conversion_required(full_path), needs_conversion)

    def test_subtitle_detection(self):
        self._test_content("12:34:56:test", True)
        self._test_content("{1}{2}test", True)
        self._test_content("12:34:56:test\n21:01:45:test2", True)
        self._test_content("12:34:5:test", False)
        self._test_content("12:test", False)
        self._test_content("{12}:test", False)
        self._test_content("{a}{b}:test", False)


if __name__ == '__main__':
    unittest.main()
