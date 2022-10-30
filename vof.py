
import os
import sys
import subprocess
import tempfile
import shutil


if len(sys.argv) != 3:
    print(f"python {sys.argv[0]} video1 video2")
    exit(1)

file1 = sys.argv[1]
file2 = sys.argv[2]

temp_location = tempfile.gettempdir() + "/VOF/" + str(os.getpid()) + "/"
os.makedirs(name = temp_location)

#filters to be consedered: atadenoise,hue=s=0,scdet=s=1:t=10
subprocess.run(["ffmpeg", "-i", file1, "-filter:v", "select=gt(scene\,0.4),showinfo", "-fps_mode",
                "passthrough", temp_location + "lhs%05d.jpg"], capture_output=True)
subprocess.run(["ffmpeg", "-i", file2, "-filter:v", "select=gt(scene\,0.4),showinfo", "-fps_mode",
                "passthrough", temp_location + "rhs%05d.jpg"], capture_output=True)

print("{}")
shutil.rmtree(temp_location)
