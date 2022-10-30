
import os
import re
import sys
import subprocess
import shutil
import tempfile


def process_video(path: str, wd: str) -> dict:
    os.makedirs(name = wd)
    process = subprocess.Popen(["ffmpeg", "-hide_banner", "-nostats", "-i", path, "-filter:v", "select=gt(scene\,0.3),showinfo",
                               "-fps_mode", "passthrough", wd + "/%05d.jpg"],
                              stderr=subprocess.PIPE)

    result = dict()

    while True:
        line_raw = process.stderr.readline()
        if not line_raw:
            break

        line = line_raw.decode("utf-8")
        if line[1:18] == "Parsed_showinfo_1":
            matched = re.search("^\[Parsed_showinfo_1.+ n: +([0-9]+) .+ pts_time:([0-9\.]+).+", line)

            if matched:
                frame_id = int(matched.group(1)) + 1
                time_sig = float(matched.group(2))

                result[frame_id] = time_sig

    return result


if len(sys.argv) != 3:
    print(f"python {sys.argv[0]} video1 video2")
    exit(1)

file1 = sys.argv[1]
file2 = sys.argv[2]

temp_location = tempfile.gettempdir() + "/VOF/" + str(os.getpid()) + "/"

#filters to be consedered: atadenoise,hue=s=0,scdet=s=1:t=10
video1_scenes = process_video(file1, temp_location + "1")
video2_scenes = process_video(file2, temp_location + "2")

print("{}")
shutil.rmtree(temp_location)
