
import subprocess

def length(path: str) -> float:
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


def fps(path: str) -> float:
    status = subprocess.run(["ffprobe",
                             "-v",
                             "error",
                             "-show_entries",
                             "stream=r_frame_rate",
                             "-of",
                             "default=noprint_wrappers=1:nokey=1",
                             path],
                            capture_output=True)
    fps_str = status.stdout
    fps = eval(fps_str)
    return fps
