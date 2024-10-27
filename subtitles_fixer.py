
import argparse
import logging
import os
import re
import shutil
import sys
import tempfile

import utils


class Fixer:
    def __init__(self):
        self._work = True

    def _extract_all_subtitles(self, video_file: str, subtitles: [utils.Subtitle], wd: str) -> [str]:
        result = []
        for subtitle in subtitles:
            outputfile = f"{wd}/{subtitle.tid}.srt"
            utils.start_process("mkvextract", ["tracks", video_file, f"{subtitle.tid}:{outputfile}"])
            result.append(outputfile)

        return result

    def _fix_subtitle(self, broken_subtitle, target_fps):
        multiplier = utils.ffmpeg_default_fps / target_fps

        def multiply_time(match):
            time_from, time_to = map(utils.time_to_ms, match.groups())
            time_from *= multiplier
            time_to *= multiplier

            time_from_srt = utils.ms_to_time(time_from)
            time_to_srt = utils.ms_to_time(time_to)

            return f"{time_from_srt} --> {time_to_srt}"

        with open(broken_subtitle, 'r', encoding='utf-8') as file:
            content = file.read()

        new_content = utils.subrip_time_pattern.sub(multiply_time, content)

        with open(broken_subtitle, 'w', encoding='utf-8') as file:
            file.write(new_content)


    def _process_video(self, video_file: str):
        logging.debug(f"Processing file {video_file}")

        def diff(a, b):
            return abs(a - b) / max(a, b)

        video_info = utils.get_video_data(video_file)
        video_length = video_info.video_tracks[0].length

        broken_subtitiles = []

        for i in range(len(video_info.subtitles)):
            subtitle = video_info.subtitles[i]
            lenght = subtitle.length
            if lenght is not None and lenght > video_length * 1.001:                 # use 0.1% error margin as for some reason valid subtitles may appear longer than video
                broken_subtitiles.append(i)

        if len(broken_subtitiles) == 0:
            return

        with tempfile.TemporaryDirectory() as wd_dir:
            subtitles = self._extract_all_subtitles(video_file, video_info.subtitles, wd_dir)
            broken_subtitles_paths = [subtitles[i] for i in broken_subtitiles]

            for broken_subtitile in broken_subtitles_paths:
                self._fix_subtitle(broken_subtitile, utils.fps_str_to_float(video_info.video_tracks[0].fps))



    def _process_dir(self, path: str):
        video_files = []
        for entry in os.scandir(path):
            if entry.is_file() and utils.is_video(entry.path):
                video_files.append(entry.path)
            elif entry.is_dir():
                self.process_dir(entry.path)

        for video_file in video_files:
            self._process_video(video_file)

    def process_dir(self, path: str):
        self._process_dir(path)

    def stop(self):
        self._work = False


def run(sys_args: [str]):
    parser = argparse.ArgumentParser(description='Look for MKV movies with subtitles with invalid fps and try to fix them.')

    parser.add_argument("--no-dry-run", "-r",
                        action='store_true',
                        default=False,
                        help='Perform actual operation.')
    parser.add_argument('videos_path',
                        nargs=1,
                        help='Path with videos to analyze.')
    parser.add_argument("--verbose", action='store_true', default=False, help='Verbose output')

    args = parser.parse_args(sys_args)

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    for tool in ["mkvmerge", "mkvextract", "ffprobe"]:
        path = shutil.which(tool)
        if path is None:
            raise RuntimeError(f"{tool} not found in PATH")
        else:
            logging.debug(f"{tool} path: {path}")

    logging.info("Searching for broken files")
    fixer = Fixer()
    fixer.process_dir(args.videos_path[0])


if __name__ == '__main__':
    logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.INFO)
    try:
        run(sys.argv[1:])
    except RuntimeError as e:
        logging.error(f"Unexpected error occurred: {e}. Terminating")
        exit(1)

    logging.info("Done")
