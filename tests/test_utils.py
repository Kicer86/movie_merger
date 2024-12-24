
import os
import unittest

import twotone.tools.utils as utils
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


if __name__ == '__main__':
    unittest.main()
