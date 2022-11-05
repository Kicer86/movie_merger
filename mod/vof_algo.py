
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


def are_keyframes_in_sync(video1_keyframes: [], video2_keyframes: [],
                          video1_fps: float, video2_fps: float) -> bool:
    assert len(video1_keyframes) == len(video2_keyframes)
    assert len(video1_keyframes) > 1

    deltas = [abs(lhs_time - rhs_time) for lhs_time, rhs_time in zip(video1_keyframes, video2_keyframes)]
    avg_delta = sum(deltas)/len(deltas)
    delta_diffs = [abs(delta - avg_delta) for delta in deltas]
    max_diff = max(delta_diffs)

    # find what is the frame duration of video with lower fps
    min_fps = min([video1_fps, video2_fps])
    frame_duration = 1 / min_fps

    return frame_duration >= max_diff


def adjust_videos(video1_keyframes: [], video2_keyframes: [],
                  video1_fps: float, video2_fps: float,
                  video1_length: float, video2_length: float) -> {}:
    assert len(video1_keyframes) == len(video2_keyframes)
    assert len(video1_keyframes) > 1

    if not are_keyframes_in_sync(video1_keyframes, video2_keyframes, video1_fps, video2_fps):
        # calculate % of diff for first and last frame
        first_diff_percent = video1_keyframes[0] / video2_keyframes[0]
        last_diff_percent = video1_keyframes[-1] / video2_keyframes[-1]

        # apply correction for all scenes and video length
        avg_percent = (first_diff_percent + last_diff_percent) / 2
        video2_keyframes = [timestamp * avg_percent for timestamp in video2_keyframes]
        video2_length *= avg_percent

    video1_begin = video1_keyframes[0] - video2_keyframes[0] if video1_keyframes[0] > video2_keyframes[0] else 0.0
    video2_begin = video2_keyframes[0] - video1_keyframes[0] if video2_keyframes[0] > video1_keyframes[0] else 0.0

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
