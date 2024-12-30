
import logging
import os
import unittest

import twotone.tools.utils as utils
import twotone.twotone as twotone
from common import TestDataWorkingDirectory, add_test_media, hashes
from unittest.mock import patch


class SimpleSubtitlesMerge(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls._start_process = utils.start_process
        logging.getLogger().setLevel(logging.CRITICAL)


    def test_no_changes_when_mkvmerge_exits_with_error(self):

        def start_process(cmd, args):
            _, exec_name, _ = utils.split_path(cmd)

            if exec_name == "mkvmerge":
                return utils.ProcessResult(1, b"", b"")
            else:
                return self._start_process.__func__(cmd, args)

        with patch("twotone.tools.utils.start_process") as mock_start_process, TestDataWorkingDirectory() as td:
            mock_start_process.side_effect = start_process
            add_test_media("Blue_Sky_and_Clouds_Timelapse.*(?:mov|srt)", td.path)

            hashes_before = hashes(td.path)
            self.assertEqual(len(hashes_before), 2)
            try:
                twotone.execute(["--no-dry-run", "merge", td.path])
            except RuntimeError:
                pass

            hashes_after = hashes(td.path)

            self.assertEqual(hashes_before, hashes_after)
            self.assertEqual(mock_start_process.call_count, 3)


    def test_no_changes_when_ffprobe_exits_with_error(self):

        def start_process(cmd, args):
            _, exec_name, _ = utils.split_path(cmd)

            if exec_name == "ffprobe":
                return utils.ProcessResult(1, b"", b"")
            else:
                return self._start_process.__func__(cmd, args)

        with patch("twotone.tools.utils.start_process") as mock_start_process, TestDataWorkingDirectory() as td:
            mock_start_process.side_effect = start_process
            add_test_media("Blue_Sky_and_Clouds_Timelapse.*(?:mov|srt)", td.path)

            hashes_before = hashes(td.path)
            self.assertEqual(len(hashes_before), 2)
            try:
                twotone.execute(["--no-dry-run", "merge", td.path])
            except RuntimeError:
                pass

            hashes_after = hashes(td.path)

            self.assertEqual(hashes_before, hashes_after)
            self.assertEqual(mock_start_process.call_count, 1)

    def test_no_changes_when_ffmpeg_exits_with_error(self):

        def start_process(cmd, args):
            _, exec_name, _ = utils.split_path(cmd)

            if exec_name == "ffmpeg":
                return utils.ProcessResult(1, b"", b"")
            else:
                return self._start_process.__func__(cmd, args)

        with patch("twotone.tools.utils.start_process") as mock_start_process, TestDataWorkingDirectory() as td:
            mock_start_process.side_effect = start_process
            add_test_media("Blue_Sky_and_Clouds_Timelapse.*(?:mov|srt)", td.path)

            hashes_before = hashes(td.path)
            self.assertEqual(len(hashes_before), 2)
            try:
                twotone.execute(["--no-dry-run", "merge", td.path])
            except RuntimeError:
                pass

            hashes_after = hashes(td.path)

            self.assertEqual(hashes_before, hashes_after)
            self.assertEqual(mock_start_process.call_count, 2)


if __name__ == '__main__':
    unittest.main()
