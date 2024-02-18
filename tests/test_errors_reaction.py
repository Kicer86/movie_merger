
import os
import unittest

import twotone
import utils
from common import TestDataWorkingDirectory, add_test_media, hashes
from unittest.mock import patch


class SimpleSubtitlesMerge(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls._start_process = utils.start_process

    @patch("utils.start_process")
    def test_no_changes_when_mkvmerge_exits_with_error(self, mock_start_process):

        def start_process(cmd, args):
            _, exec_name, _ = utils.split_path(cmd)

            if exec_name == "mkvmerge":
                return utils.ProcessResult(1, b"", b"")
            else:
                return self._start_process.__func__(cmd, args)

        mock_start_process.side_effect = start_process

        with TestDataWorkingDirectory() as td:
            add_test_media("Blue_Sky_and_Clouds_Timelapse.*(?:mov|srt)", td.path)

            hashes_before = hashes(td.path)
            self.assertEqual(len(hashes_before), 2)
            try:
                twotone.run([td.path, "--no-dry-run"])
            except RuntimeError:
                pass

            hashes_after = hashes(td.path)

            self.assertEqual(hashes_before, hashes_after)
            self.assertEqual(mock_start_process.call_count, 3)

    @patch("utils.start_process")
    def test_no_changes_when_ffprobe_exits_with_error(self, mock_start_process):

        def start_process(cmd, args):
            _, exec_name, _ = utils.split_path(cmd)

            if exec_name == "ffprobe":
                return utils.ProcessResult(1, b"", b"")
            else:
                return self._start_process.__func__(cmd, args)

        mock_start_process.side_effect = start_process

        with TestDataWorkingDirectory() as td:
            add_test_media("Blue_Sky_and_Clouds_Timelapse.*(?:mov|srt)", td.path)

            hashes_before = hashes(td.path)
            self.assertEqual(len(hashes_before), 2)
            try:
                twotone.run([td.path, "--no-dry-run"])
            except RuntimeError:
                pass

            hashes_after = hashes(td.path)

            self.assertEqual(hashes_before, hashes_after)
            self.assertEqual(mock_start_process.call_count, 1)


    @patch("utils.start_process")
    def test_no_changes_when_ffmpeg_exits_with_error(self, mock_start_process):

        def start_process(cmd, args):
            _, exec_name, _ = utils.split_path(cmd)

            if exec_name == "ffmpeg":
                return utils.ProcessResult(1, b"", b"")
            else:
                return self._start_process.__func__(cmd, args)

        mock_start_process.side_effect = start_process

        with TestDataWorkingDirectory() as td:
            add_test_media("Blue_Sky_and_Clouds_Timelapse.*(?:mov|srt)", td.path)

            hashes_before = hashes(td.path)
            self.assertEqual(len(hashes_before), 2)
            try:
                twotone.run([td.path, "--no-dry-run"])
            except RuntimeError:
                pass

            hashes_after = hashes(td.path)

            self.assertEqual(hashes_before, hashes_after)
            self.assertEqual(mock_start_process.call_count, 2)

if __name__ == '__main__':
    unittest.main()
