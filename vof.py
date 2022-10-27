
import sys
import subprocess


if len(sys.argv) != 3:
    print(f"python {sys.argv[0]} video1 video2")
    exit(1)

file1 = sys.argv[1]
file2 = sys.argv[2]

subprocess.run(["ffmpeg", "-i", file1, "-filter:v", "select=gt(scene\,0.4),showinfo", "-fps_mode",
                "passthrough", "frames/%05d.jpg"])
