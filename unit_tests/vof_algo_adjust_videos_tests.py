
import unittest

import sys
sys.path.append("..")

import vof_algo


class TestVOFAlgorithms(unittest.TestCase):

    def test_adjust_same_videos(self):
        video1_frames = [11.50, 15.49, 20.1, 31.23]
        video2_frames = [11.51, 15.51, 20.0, 31.22]

        result = vof_algo.adjust_videos(video1_frames, video2_frames,
                                        video1_fps=30, video2_fps=24,
                                        video1_length=35.45, video2_length=35.44)

        expected_result = {
            "segments": [
                {
                    "#1": {
                        "begin": 0.0,
                        "end": 35.45
                    },
                    "#2": {
                        "begin": 0.0,
                        "end": 35.44
                    }
                }
            ]
        }

        self.assertEqual(result, expected_result)


if __name__ == '__main__':
    unittest.main()
