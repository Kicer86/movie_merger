
import os
import unittest

import twotone
import utils
from common import TestDataWorkingDirectory, list_files, add_test_media, hashes
from unittest.mock import patch


class SimpleSubtitlesMerge(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls._start_process = utils.start_process

    @patch("utils.start_process")
    def test_mkvmerge_returns_with_error(self, mock_start_process):

        def start_process(cmd, args):
            print(f"mocking '{cmd}' '{args}'")
            if cmd == "ffprobe":
                return self._start_process.__func__(cmd, args)
            else:
                return utils.ProcessResult(0, b"", b"")

        mock_start_process.side_effect = start_process

        with TestDataWorkingDirectory() as td:
            add_test_media("Blue_Sky_and_Clouds_Timelapse.*(?:mov|srt)", td.path)

            hashes_before = hashes(td.path)
            self.assertEqual(len(hashes_before), 2)
            twotone.run([td.path, "--dry-run"])
            hashes_after = hashes(td.path)

            self.assertEqual(hashes_before, hashes_after)


if __name__ == '__main__':
    unittest.main()
