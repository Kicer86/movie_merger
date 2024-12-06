
import unittest
import logging

import encode
from common import TestDataWorkingDirectory
from test_utils import video_cache


class Encode(unittest.TestCase):

    def test_video_1_for_best_crf(self):
        test_video = video_cache.fetch("video321/mp4/720/big_buck_bunny_720p_2mb.mp4")
        best_enc = encode.find_optimal_crf(test_video, allow_segments=False)

        self.assertEqual(best_enc, 28)

    def test_video_2_segments_for_best_crf(self):
        test_video = video_cache.fetch("video321/mp4/720/big_buck_bunny_720p_10mb.mp4")
        best_enc = encode.find_optimal_crf(test_video, allow_segments=True)

        self.assertEqual(best_enc, 30)

    def test_video_2_nosegments_for_best_crf(self):
        return
        test_video = video_cache.fetch("video321/mp4/720/big_buck_bunny_720p_10mb.mp4")
        best_enc = encode.find_optimal_crf(test_video, allow_segments=False)

        self.assertEqual(best_enc, 29)


if __name__ == '__main__':
    logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.ERROR)
    unittest.main()
