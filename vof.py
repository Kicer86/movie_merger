
import json
import os
import re
import sys
import subprocess
import shutil
import tempfile

import video_probing


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


if len(sys.argv) != 3:
    print(f"python {sys.argv[0]} video1 video2")
    exit(1)

video1 = sys.argv[1]
video2 = sys.argv[2]

temp_location = tempfile.gettempdir() + "/VOF/" + str(os.getpid()) + "/"

# filters to be consedered: atadenoise,hue=s=0,scdet=s=1:t=10
video1_scenes = process_video(video1, temp_location + "1")
video2_scenes = process_video(video2, temp_location + "2")

output = {}
# perform matching
if len(video1_scenes) == len(video2_scenes):
    # Count of scene changes match, try to map them
    deltas = []
    for lhs_time, rhs_time in zip(video1_scenes, video2_scenes):
        deltas.append(lhs_time - rhs_time)

    max_delta = max(deltas)

    # find what is the frame duration of video with lower fps
    video1_fps = video_probing.fps(video1)
    video2_fps = video_probing.fps(video2)

    min_fps = min([video1_fps, video2_fps])
    frame_duration = 1 / min_fps

    # if frame_duration is bigger than biggest delta, then no work to be done
    if frame_duration < max_delta:
        pass                        # for now

    video1_segment = dict()
    video1_segment["begin"] = 0.0
    video1_segment["end"] = video_probing.length(video1)

    video2_segment = dict()
    video2_segment["begin"] = 0.0
    video2_segment["end"] = video_probing.length(video2)

    segments = [
        {video1: video1_segment},
        {video2: video2_segment}
    ]

    output["segments"] = segments

print(json.dumps(output))
shutil.rmtree(temp_location)
