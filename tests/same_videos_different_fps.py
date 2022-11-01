
import sys
sys.path.append("..")

import json
import subprocess
import sys

import video_probing


vof_script = sys.argv[1]
test_videos_dir = sys.argv[2]

video_pairs=[("movie-2160p.mp4", "movie-360p.mp4"),
             ("movie-720p-ntsc_fps.mp4", "movie-360p.mp4"),
             ("movie-720p-ntsc_film_fps.mp4", "movie-720p-120_fps.mp4"),
             ("movie-720p-film_fps.mp4", "movie-720p-20_fps.mp4")]

passes = 0

for (video1, video2) in video_pairs:

    video1_path = test_videos_dir + "/" + video1
    video2_path = test_videos_dir + "/" + video2

    print(f"Starting VOF for:\n{video1_path}\n{video2_path}")
    status = subprocess.run(["python", vof_script, video1_path, video2_path],
                            capture_output=True)

    if status.returncode != 0:
        print("VOF exited with error")
        exit(1)

    output = json.loads(status.stdout)

    # verify overlapping regions
    if not "segments" in output:
        print("Segments were expected")
        exit(1)

    segments = output["segments"]

    if len(segments) != 1:
        print("1 segment was expected")
        exit(1)

    segment_scope = segments[0]

    try:
        video1_segment_details = segment_scope.get("#1")
        video2_segment_details = segment_scope.get("#2")

        video1_segment_begin = video1_segment_details.get("begin")
        video2_segment_begin = video2_segment_details.get("begin")
        video1_segment_end = video1_segment_details.get("end")
        video2_segment_end = video2_segment_details.get("end")

        video1_len = video_probing.length(video1_path)
        video2_len = video_probing.length(video2_path)

        if video1_segment_begin != 0.0 or video1_segment_end != video1_len or video2_segment_begin != 0.0 or video2_segment_end != video2_len:
            print("Videos are not overlapped in the expected way")
            exit(1)

        passes = passes + 1

    except:
        print("No valid segments data")
        exit(1)

if passes == len(video_pairs):
    print("All cases passed")
else:
    print("Some tests failed")
    exit(1)
