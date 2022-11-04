
import json
import os
import subprocess
import sys
import tempfile

import mod.vof_algo as vof_algo
import mod.video_probing as video_probing


def load_recipe(path: str) -> dict:
    data = dict()

    with open(path, 'r') as f:
        data = json.load(f)

    return data


def process_recipe(recipe: dict):
    try:
        files = recipe.get("files")
        assert len(files) == 2              # TODO: handling many files at once would be nice

        # when vof.py is read, "common timestamps" will be replaced with "overlapping segments"
        # so no calcualtions are needed here
        common_timestamps = recipe.get("common timestamps")
        assert len(common_timestamps) > 1

        file1_timestamps = []
        file2_timestamps = []
        for timestamp_pair in common_timestamps:
            file1_timestamps.append(timestamp_pair.get("#1"))
            file2_timestamps.append(timestamp_pair.get("#2"))

        file1_fps = video_probing.fps(files[0])
        file2_fps = video_probing.fps(files[1])
        file1_len = video_probing.length(files[0])
        file2_len = video_probing.length(files[1])
        adjustments = vof_algo.adjust_videos(file1_timestamps, file2_timestamps,
                                             file1_fps, file2_fps,
                                             file1_len, file2_len)

        segments = adjustments.get("segments")
        assert len(segments) == 1           # TODO: handle more

        segment = segments[0]
        file1_segment = segment.get("#1")
        file2_segment = segment.get("#2")
        file1_begin = file1_segment.get("begin")
        file1_end = file1_segment.get("end")
        file2_begin = file2_segment.get("begin")
        file2_end = file2_segment.get("end")

        temp_location = tempfile.gettempdir() + "/MKVAssembler/" + str(os.getpid()) + "/"
        os.makedirs(name = temp_location)

        audio_codec_type = video_probing.audio_codec(files[1])
        audio_codec_ext = audio_codec_type
        audio_codec = "copy"
        if audio_codec_type == "cook":
            audio_codec_ext = "ogg"
            audio_codec = "libvorbis"

        process = subprocess.Popen(["ffmpeg", "-hide_banner", "-nostats", "-i", files[1], "-vn", "-acodec", audio_codec,
                                    temp_location + "file2_audio." + audio_codec_ext]
                                   )
        process.wait()


    except:
        print("Invalid recipe structure")
        exit(1)


if len(sys.argv) != 2:
    print(f"python {sys.argv[0]} recipe.json")
    exit(1)

recipe = load_recipe(sys.argv[1])
process_recipe(recipe)


# recipe structure:
#
# {
#   "files": ["file1,avi", "file2.mp4", "file3.mp4"],
#   "common timestamps": [
#     { "#1": 12.34, "#2": 12.34 },
#     { "#1": 25.7,  "#2": 25.6 }
#   ]
# }
#
