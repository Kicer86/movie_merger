
import argparse
import logging
import os
import subprocess
import sys
from pathlib import Path

import utils


class TwoTone:

    def __init__(self, use_mime: bool, dry_run: bool, language: str):
        self.use_mime = use_mime
        self.dry_run = dry_run
        self.language = language

    def _split_path(self, path: str) -> (str, str, str):
        info = Path(path)

        return str(info.parent), info.stem, info.suffix[1:]

    def _simple_subtitle_search(self, path: str) -> [str]:
        video_name = Path(path).stem
        dir = Path(path).parent

        subtitles = []

        for subtitle_ext in ["txt", "srt"]:
            subtitle_file = video_name + "." + subtitle_ext
            subtitle_path = os.path.join(dir, subtitle_file)
            if os.path.exists(subtitle_path):
                subtitles.append(subtitle_path)

        return subtitles


    def _aggressive_subtitle_search(self, path: str) -> [str]:
        return self._simple_subtitle_search(path)


    def _run_mkvmerge(self, options: [str]) -> bool:
        if not self.dry_run:
            process = ["mkvmerge"]
            process.extend(options)
            result = subprocess.run(process, capture_output = True)

            logging.debug(result.stdout)

            if result.stderr:
                logging.error(result.stderr)

            return result.returncode == 0
        else:
            return False


    def _merge(self, input_video: str, subtitles: [str]):
        logging.info(f"Video file: {input_video}")
        for subtitle in subtitles:
            logging.info(f"\tadd subtitles: {subtitle}")

        video_dir, video_name, video_extension = self._split_path(input_video)
        tmp_video = video_dir + "/." + video_name + "." + "mkv"
        output_video = video_dir + "/" + video_name + "." + "mkv"

        options = ["-o", tmp_video, input_video]

        for subtitle in subtitles:
            if self.language:
                options.append("--language")
                options.append("0:" + self.language)

            options.append(subtitle)

        status = self._run_mkvmerge(options)

        if not self.dry_run and status and os.path.exists(tmp_video):
            to_remove = [input_video]
            to_remove.extend(subtitles)

            for file_to_remove in to_remove:
                os.remove(file_to_remove)
                pass

            os.rename(tmp_video, output_video)


    def process_dir(self, path: str):
        video_files = []
        for entry in os.scandir(path):
            if entry.is_file() and utils.is_video(entry.path, self.use_mime):
                video_files.append(entry.path)
            elif entry.is_dir():
                self.process_dir(entry.path)

        if len(video_files) == 1:
            video_file = video_files[0]
            subtitles = self._aggressive_subtitle_search(video_file)
            if subtitles:
                self._merge(video_file, subtitles)
        if len(video_files) > 1:
            for video_file in video_files:
                subtitles = self._simple_subtitle_search(video_file)
                if subtitles:
                    self._merge(video_file, subtitles)


def run(sys_args: [str]):
    parser = argparse.ArgumentParser(description='Combine many video/subtitle files into one mkv file.')
    parser.add_argument('--analyze-mime',
                        action = 'store_true',
                        default = False,
                        help = 'Use file mime type instead of file extension for video files recognition. It is slower but more accurate.')
    parser.add_argument('videos_path',
                        nargs = 1,
                        help = 'Path with videos to combine')
    parser.add_argument("--dry-run", "-n",
                        action = 'store_true',
                        default = False,
                        help = 'No not modify any file, just print what will happen')

    parser.add_argument("--language", "-l",
                        help = 'Language code for found subtitles. By default none is used. See mkvmerge --list-languages for available languages')

    args = parser.parse_args(sys_args)

    two_tone = TwoTone(use_mime = args.analyze_mime, dry_run = args.dry_run, language = args.language)
    two_tone.process_dir(args.videos_path[0])


if __name__ == '__main__':
    logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.INFO)
    logging.info("Searching for movie and subtitle files to be merged")
    run(sys.argv[1:])
    logging.info("Done")
