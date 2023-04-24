
import magic
import os
import sys
from pathlib import Path


class TwoTone:

    def __init__(self, use_mime: bool):
        self.use_mime = use_mime


    def _simple_subtitle_search(self, path: str) -> [str]:
        video_name = Path(path).stem
        video_extension = Path(path).suffix
        dir = Path(path).parent

        subtitles = []

        for subtitle_ext in ["txt", "srt"]:
            subtitle_file = video_name + "." + subtitle_ext
            subtitle_path = os.path.join(dir, subtitle_file)
            if os.path.exists(subtitle_file):
                subtitles.append(subtitle_file)

        return subtitles


    def _aggressive_subtitle_search(self, path: str):
        self._simple_subtitle_search(path)
        pass


    def _is_video(self, file: str):
        mime = magic.from_file(file, mime=True)
        return mime[:5] == "video"


    def process_dir(self, path: str):
        video_files = []
        for entry in os.scandir(path):
            if entry.is_file() and self._is_video(entry.path):
                video_files.append(entry.path)
            elif entry.is_dir():
                self.process_dir(entry.path)

        if len(video_files) == 1:
            self._aggressive_subtitle_search(video_files[0])
        if len(video_files) > 1:
            for video_file in video_files:
                self._simple_subtitle_search(video_file)


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Provide path to scan")
        exit(1)

    videos_path = sys.argv[1]

    two_tone = TwoTone(False)
    two_tone.process_dir(videos_path)
