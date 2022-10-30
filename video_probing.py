
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
