
import subprocess
import sys

vof_script = sys.argv[1]
test_videos_dir = sys.argv[2]

subprocess.run(["python", vof_script, test_videos_dir + "/movie-2160p.mp4", test_videos_dir + "/movie-360p.mp4"])
