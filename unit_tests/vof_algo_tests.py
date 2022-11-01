
import unittest
import numpy as np

import sys
sys.path.append("..")

import vof_algo


class TestVOFAlgorithms(unittest.TestCase):

    def test_match_frames(self):
        scene1 = np.array([1, 2, 3, 4])
        scene2 = np.array([2, 3, 4, 5])
        scene3 = np.array([3, 4, 5, 6])
        scene4 = np.array([4, 5, 6, 7])
        scene5 = np.array([5, 6, 7, 8])
        scene6 = np.array([6, 7, 8, 9])
        scene7 = np.array([0, 1, 2, 3])

        #                0       1       2       3       4       5
        video1_scenes = [scene1, scene3, scene4, scene5, scene6]
        video2_scenes = [scene1, scene2, scene3, scene4, scene6, scene7]

        matches = vof_algo.match_frames(video1_scenes, video2_scenes)

        expected_matches = [(0, 0), (1, 2), (2, 3), (4, 4)]

        self.assertEqual(set(matches), set(expected_matches))


if __name__ == '__main__':
    unittest.main()
