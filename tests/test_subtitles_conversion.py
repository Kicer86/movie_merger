
import os
import unittest

import twotone
import utils
from common import TestDataWorkingDirectory, list_files, add_test_media, generate_microdvd_subtitles


class SubtitlesConversion(unittest.TestCase):

    def test_nondefault_fps(self):

        with TestDataWorkingDirectory() as td:
            add_test_media("sea-waves-crashing-on-beach-shore.*mp4", td.path)
            generate_microdvd_subtitles(os.path.join(td.path, "sea-waves.txt"), 25)

            twotone.run([td.path, "-l", "auto", "--no-dry-run"])

            files_after = list_files(td.path)
            self.assertEqual(len(files_after), 1)

            video = files_after[0]

            subtitles_path = os.path.join(td.path, "subtitles.srt")
            utils.start_process("ffmpeg", ["-i", video, "-map", "0:s:0", subtitles_path])

            with open(subtitles_path, mode='r') as subtitles_file:
                ms_time = 0
                for line in subtitles_file:
                    match = utils.subrip_time_pattern.match(line.strip())
                    if match:
                        start_time, end_time = match.groups()
                        start_ms = utils.time_to_ms(start_time)
                        end_ms = utils.time_to_ms(end_time)

                        # one millisecond difference is acceptable (hence delta = 1)
                        self.assertAlmostEqual(start_ms, ms_time, delta = 1)
                        self.assertAlmostEqual(end_ms, ms_time + 500, delta = 1)
                        ms_time += 1000


if __name__ == '__main__':
    unittest.main()
