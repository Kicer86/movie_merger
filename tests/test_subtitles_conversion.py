
import os
import unittest

import twotone
import utils
from common import TestDataWorkingDirectory, list_files, add_test_media


class SubtitlesConversion(unittest.TestCase):

    def test_nondefault_fps(self):
        with TestDataWorkingDirectory() as td:
            add_test_media("sea-waves-crashing-on-beach-shore.*mp4", td.path)

            with open(os.path.join(td.path, "sea-waves.txt"), "w") as sf:
                sf.write("{60}{120}Hello World\n")
                sf.write("{240}{360}This is some sample subtitle in english\n")
                sf.write("{360}{480}THE END\n")

            twotone.run([td.path, "-l", "auto", "--no-dry-run"])

            files_after = list_files(td.path)
            self.assertEqual(len(files_after), 1)

            video = files_after[0]

            subtitles_path = os.path.join(td.path, "subtitles.srt")
            utils.start_process("ffmpeg", ["-i", video, "-map", "0:s:0", subtitles_path])

            with open(subtitles_path, mode='r') as subtitles_file:
                content = subtitles_file.read()
                stipped_content = content.strip()

                expected_content = (
                    "1\n"
                    "00:00:01,000 --> 00:00:02,000\n"
                    "Hello World\n\n"
                    "2\n"
                    "00:00:04,000 --> 00:00:06,000\n"
                    "This is some sample subtitle in english\n\n"
                    "3\n"
                    "00:00:06,000 --> 00:00:08,000\n"
                    "THE END").strip()

                self.assertEqual(stipped_content, expected_content)


if __name__ == '__main__':
    unittest.main()
