
import numpy as np

def match_frames(video1_hashes: [], video2_hashes: []) -> []:
    # O^2 solution, but maybe it will do
    matches = []

    for i in range(len(video1_hashes)):
        for j in range(len(video2_hashes)):
            if np.array_equal(video1_hashes[i], video2_hashes[j]):
                matches.append((i, j))
                break

    return matches
