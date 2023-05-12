
import sys
sys.path.append("..")

import os
import unittest

import utils
from common import TestDataWorkingDirectory


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

    def test_conversion_requirement(self):
        with TestDataWorkingDirectory() as wd:
            with open(os.path.join(wd.path, "subtitle_1.srt"), "w") as sf:
                sf.write("00:00:00:Hello World\n")
                sf.write("00:00:06:This is some sample subtitle in english\n")

            with open(os.path.join(wd.path, "subtitle_1.txt"), "w") as sf:
                sf.write("00:00:00:Hello World\n")
                sf.write("00:00:06:This is some sample subtitle in english\n")

            with open(os.path.join(wd.path, "subtitle_2.srt"), "w") as sf:
                sf.write("{0}{5000}:Hello World\n")
                sf.write("{6000}{12000}:This is some sample subtitle in english\n")

            with open(os.path.join(wd.path, "subtitle_2.txt"), "w") as sf:
                sf.write("{0}{5000}:Hello World\n")
                sf.write("{6000}{12000}:This is some sample subtitle in english\n")

            with open(os.path.join(wd.path, "subtitle_3.srt"), "w") as sf:
                sf.write("1\n")
                sf.write("00:00:00,000 --> 00:00:05,000\n")
                sf.write("Hello World\n")
                sf.write("2\n")
                sf.write("00:00:06,000 --> 00:00:12,000\n")
                sf.write("This is some sample subtitle in english\n")

            with open(os.path.join(wd.path, "subtitle_3.txt"), "w") as sf:
                sf.write("1\n")
                sf.write("00:00:00,000 --> 00:00:05,000\n")
                sf.write("Hello World\n")
                sf.write("2\n")
                sf.write("00:00:06,000 --> 00:00:12,000\n")
                sf.write("This is some sample subtitle in english\n")

            # mkvmerge (as of now) only supports SubRip format for subtitles (file extension is not relevant)
            self._test_conversion(wd.path, "subtitle_1.srt", True)
            self._test_conversion(wd.path, "subtitle_1.txt", True)
            self._test_conversion(wd.path, "subtitle_2.srt", True)
            self._test_conversion(wd.path, "subtitle_2.txt", True)
            self._test_conversion(wd.path, "subtitle_3.srt", False)
            self._test_conversion(wd.path, "subtitle_3.txt", False)


if __name__ == '__main__':
    unittest.main()
