
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


def adjust_videos(video1_scenes: [], video2_scenes: [],
                  video1_fps: int, video2_fps: int,
                  video1_length: float, video2_length: float) -> {}:
    deltas = []
    for lhs_time, rhs_time in zip(video1_scenes, video2_scenes):
        deltas.append(lhs_time - rhs_time)

    max_delta = max(deltas)

    # find what is the frame duration of video with lower fps
    min_fps = min([video1_fps, video2_fps])
    frame_duration = 1 / min_fps

    # if frame_duration is bigger than biggest delta, then no work to be done
    if frame_duration < max_delta:
        pass  # for now

    video1_segment = dict()
    video1_segment["begin"] = 0.0
    video1_segment["end"] = video1_length

    video2_segment = dict()
    video2_segment["begin"] = 0.0
    video2_segment["end"] = video2_length

    segment_scope = {
        "#1": video1_segment,
        "#2": video2_segment
    }

    segments = [segment_scope]

    output = {"segments": segments}
    return output
