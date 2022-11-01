
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
    fps_bytes = status.stdout
    fps_str = fps_bytes.decode("utf-8")
    fps_list = fps_str.split("\n")
    valid_fps = [fps for fps in fps_list if len(fps) > 0 and fps[0] != "0"]
    fps_line = valid_fps[0]
    fps = eval(fps_line)
    return fps
