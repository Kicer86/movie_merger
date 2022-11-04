
import cv2 as cv
import json
import numpy as np
import os
import re
import sys
import subprocess
import shutil
import tempfile

import mod.video_probing as video_probing
import mod.vof_algo as vof_algo


def process_video(path: str, wd: str) -> []:
    os.makedirs(name = wd)
    process = subprocess.Popen(["ffmpeg", "-hide_banner", "-nostats", "-i", path, "-filter:v", "scale=-1:240,select=gt(scene\,0.3),showinfo",
                               "-fps_mode", "passthrough", wd + "/%05d.jpg"],
                              stderr=subprocess.PIPE)

    result = []

    while True:
        line_raw = process.stderr.readline()
        if not line_raw:
            break

        line = line_raw.decode("utf-8")
        if line[1:17] == "Parsed_showinfo_":
            matched = re.search("^\[Parsed_showinfo_.+ n: +([0-9]+) .+ pts_time:([0-9\.]+).+", line)

            if matched:
                frame_id = int(matched.group(1)) + 1
                time_sig = float(matched.group(2))

                result.append(time_sig)

    return result


def generate_hashes(scenes_location: str) -> []:
    images = [os.path.join(scenes_location, img) for img in os.listdir(scenes_location)
              if os.path.isfile(os.path.join(scenes_location, img))]

    hashes = [None for i in range(len(images))]
    for image_path in images:
        image = cv.imread(image_path)
        img_hash = cv.img_hash.blockMeanHash(image)
        # img_hash = int.from_bytes(img_hash_raw.tobytes(), byteorder='big', signed=False)
        scene_no = int(os.path.splitext(os.path.basename(image_path))[0]) - 1   # count from zero
        hashes[scene_no] = img_hash

    return hashes


output = {}

if len(sys.argv) != 3:
    print(f"python {sys.argv[0]} video1 video2")
    exit(1)

else:
    video1 = sys.argv[1]
    video2 = sys.argv[2]

    temp_location = tempfile.gettempdir() + "/VOF/" + str(os.getpid()) + "/"
    video1_scenes_location = temp_location + "1"
    video2_scenes_location = temp_location + "2"

    # filters to be considered: atadenoise,hue=s=0,scdet=s=1:t=10
    video1_scenes = process_video(video1, video1_scenes_location)
    video2_scenes = process_video(video2, video2_scenes_location)

    video1_fps = video_probing.fps(video1)
    video2_fps = video_probing.fps(video2)

    video1_len = video_probing.length(video1)
    video2_len = video_probing.length(video2)

    # perform matching
    video1_hashes = generate_hashes(video1_scenes_location)
    video2_hashes = generate_hashes(video2_scenes_location)

    # find corresponding scenes
    hash_algo = cv.img_hash.BlockMeanHash().create()
    matching_frames = vof_algo.match_frames(video1_hashes, video2_hashes,
                                            lambda l, r: hash_algo.compare(l, r) < 10)

    if len(matching_frames) > 1:
        video1_frames_with_match = []
        video2_frames_with_match = []

        for (match1, match2) in matching_frames:
            video1_frames_with_match.append(video1_scenes[match1])
            video2_frames_with_match.append(video2_scenes[match2])

        output = vof_algo.adjust_videos(video1_frames_with_match, video2_frames_with_match,
                                        video1_fps, video2_fps,
                                        video1_len, video2_len)

    shutil.rmtree(temp_location)

print(json.dumps(output))
