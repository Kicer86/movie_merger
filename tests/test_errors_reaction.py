
import os
import unittest

import twotone
import utils
from common import TestDataWorkingDirectory, list_files, add_test_media, hashes
from unittest.mock import patch


def start_process(cmd, args):
    print(cmd)
    print(args)

    return utils.ProcessResult(0, b"", b"")

class SimpleSubtitlesMerge(unittest.TestCase):

    @patch("utils.start_process", new=start_process)
    def test_mkvmerge_returns_with_error(self):
        with TestDataWorkingDirectory() as td:
            add_test_media("Blue_Sky_and_Clouds_Timelapse.*(?:mov|srt)", td.path)

            hashes_before = hashes(td.path)
            self.assertEqual(len(hashes_before), 2)
            twotone.run([td.path, "--dry-run"])
            hashes_after = hashes(td.path)

            self.assertEqual(hashes_before, hashes_after)
