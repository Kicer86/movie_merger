
import json
import subprocess
import sys


def video_length(path: str) -> float:
    status = subprocess.run(["ffprobe",
                             "-v",
                             "error",
                             "-show_entries",
                             "format=duration",
                             "-of",
                             "default=noprint_wrappers=1:nokey=1",
                             path],
                            capture_output=True)
    length = float(status.stdout)
    return length

vof_script = sys.argv[1]
test_videos_dir = sys.argv[2]

video_pairs=[("movie-2160p.mp4", "movie-360p.mp4"),
             ("movie-720p-ntsc_fps.mp4", "movie-360p.mp4"),
             ("movie-720p-ntsc_film_fps.mp4", "movie-720p-120_fps.mp4"),
             ("movie-720p-film_fps.mp4", "movie-720p-20_fps.mp4")]

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
    video1_len = video_length(video1_path)
    video2_len = video_length(video2_path)

    print(f"video 1 length: {video1_len}")
    print(f"video 2 length: {video2_len}")

    #print(output)
