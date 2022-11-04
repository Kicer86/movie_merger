
import cv2 as cv
import numpy as np

def match_frames(video1_hashes: [], video2_hashes: [], comp) -> []:
    # O^2 solution, but maybe it will do
    matches = []

    for i in range(len(video1_hashes)):
        for j in range(len(video2_hashes)):
            if comp(video1_hashes[i], video2_hashes[j]):
                matches.append((i, j))
                break

    return matches


def adjust_videos(video1_scenes: [], video2_scenes: [],
                  video1_fps: int, video2_fps: int,
                  video1_length: float, video2_length: float) -> {}:
    assert len(video1_scenes) == len(video2_scenes)
    assert len(video1_scenes) > 1

    deltas = [abs(lhs_time - rhs_time) for lhs_time, rhs_time in zip(video1_scenes, video2_scenes)]
    avg_delta = sum(deltas)/len(deltas)
    delta_diffs = [abs(delta - avg_delta) for delta in deltas]
    max_diff = max(delta_diffs)

    # find what is the frame duration of video with lower fps
    min_fps = min([video1_fps, video2_fps])
    frame_duration = 1 / min_fps

    video1_begin = video1_scenes[0] - video2_scenes[0] if video1_scenes[0] > video2_scenes[0] else 0.0
    video2_begin = video2_scenes[0] - video1_scenes[0] if video2_scenes[0] > video1_scenes[0] else 0.0

    # if frame_duration is bigger than the biggest diff, then no work to be done
    if frame_duration < max_diff:
        pass  # for now

    video1_segment = {
        "begin": video1_begin,
        "end": video1_length
    }

    video2_segment = {
        "begin": video2_begin,
        "end": video2_length
    }

    segment_scope = {
        "#1": video1_segment,
        "#2": video2_segment
    }

    segments = [segment_scope]

    return {"segments": segments}


def are_timestamps_equal(timestamp1: float, timestamp2: float, video1_fps: float, video2_fps: float) -> bool:
    min_fps = min([video1_fps, video2_fps])
    frame_duration = 1 / min_fps

    return abs(timestamp1 - timestamp2) < frame_duration
