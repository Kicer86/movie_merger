
import argparse
import logging
import os
import subprocess
import sys
from pathlib import Path

import utils


class TwoTone:

    def __init__(self, use_mime: bool, dry_run: bool, language: str, disable_txt: bool):
        self.use_mime = use_mime
        self.dry_run = dry_run
        self.language = language
        self.disable_txt = disable_txt
        self.to_be_removed = []

    def _remove_later(self, path: str):
        self.to_be_removed.append(path)

    def _remove(self):
        for file_to_remove in self.to_be_removed:
            os.remove(file_to_remove)
        self.to_be_removed.clear()

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
            if os.path.exists(subtitle_path) and utils.is_subtitle(subtitle_path):
                subtitles.append(subtitle_path)

        return subtitles


    def _aggressive_subtitle_search(self, path: str) -> [str]:
        subtitles = self._simple_subtitle_search(path)
        dir = Path(path).parent

        for entry in os.scandir(dir):
            if entry.is_file() and utils.is_subtitle(entry.path):
                subtitles.append(entry.path)

        return list(set(subtitles))

    def _filter_subtitles(self, subtitles: [str]) -> [str]:
        # mkvmerge does not support txt subtitles, so drop them
        return [subtitle for subtitle in subtitles if subtitle[-4:] != ".txt" or self.disable_txt == False]

    def _convert_subtitles(self, subtitles: [str]) -> [str]:
        converted_subtitles = []
        for subtitle in subtitles:
            if subtitle[-4:] == ".txt":
                subtitle_path = Path(subtitle)
                subtitle_dir = subtitle_path.parent
                subtitle_name = subtitle_path.stem
                output_subtitle = os.path.join(subtitle_dir, f".twotone_{subtitle_name}.srt")

                status = subprocess.run(["subconvert", "-c", "-o", output_subtitle, subtitle], capture_output = True)
                if status.returncode != 0:
                    raise RuntimeError("subconvert exited with unexpected error")

                converted_subtitles.append(output_subtitle)
                self._remove_later(subtitle)
            else:
                converted_subtitles.append(subtitle)

        return converted_subtitles

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
            return True


    def _merge(self, input_video: str, subtitles: [str]):
        logging.info(f"Video file: {input_video}")
        for subtitle in subtitles:
            logging.info(f"\tadd subtitles: {subtitle}")

        video_dir, video_name, video_extension = self._split_path(input_video)
        tmp_video = video_dir + "/." + video_name + "." + "mkv"
        output_video = video_dir + "/" + video_name + "." + "mkv"

        options = ["-o", tmp_video, input_video]

        self._remove_later(input_video)

        for subtitle in subtitles:
            if self.language:
                options.append("--language")
                options.append("0:" + self.language)

            options.append(subtitle)
            self._remove_later(subtitle)

        status = self._run_mkvmerge(options)

        if status:
            if not self.dry_run and os.path.exists(tmp_video):
                self._remove()
                os.rename(tmp_video, output_video)
        else:
            raise RuntimeError("mkvmerge exited with unexpected error.")

    def _process_video(self, video_file: str, subtitles_fetcher):
        all_subtitles = subtitles_fetcher(video_file)
        filtered_subtitles = self._filter_subtitles(all_subtitles)
        converted_subtitles = self._convert_subtitles(filtered_subtitles)
        if converted_subtitles:
            self._merge(video_file, converted_subtitles)

    def process_dir(self, path: str):
        video_files = []
        for entry in os.scandir(path):
            if entry.is_file() and utils.is_video(entry.path, self.use_mime):
                video_files.append(entry.path)
            elif entry.is_dir():
                self.process_dir(entry.path)

        if len(video_files) == 1:
            self._process_video(video_files[0], self._aggressive_subtitle_search)
        if len(video_files) > 1:
            for video_file in video_files:
                self._process_video(video_file, self._simple_subtitle_search)

def run(sys_args: [str]):
    parser = argparse.ArgumentParser(description='Combine many video/subtitle files into one mkv file.')
    parser.add_argument('--analyze-mime',
                        action = 'store_true',
                        default = False,
                        help = 'Use file mime type instead of file extension for video files recognition. It is slower but more accurate.')
    parser.add_argument('videos_path',
                        nargs = 1,
                        help = 'Path with videos to combine.')
    parser.add_argument("--dry-run", "-n",
                        action = 'store_true',
                        default = False,
                        help = 'No not modify any file, just print what will happen.')
    parser.add_argument("--language", "-l",
                        help = 'Language code for found subtitles. By default none is used. See mkvmerge --list-languages for available languages.')
    parser.add_argument("--disable-txt", "-t",
                        action = 'store_true',
                        default = False,
                        help = 'Disable automatic conversion txt subtitles to srt ones (txt subtitles will be ignored as mkvmerge does not understand them).')

    args = parser.parse_args(sys_args)

    two_tone = TwoTone(use_mime = args.analyze_mime,
                       dry_run = args.dry_run,
                       language = args.language,
                       disable_txt = args.disable_txt)
    two_tone.process_dir(args.videos_path[0])


if __name__ == '__main__':
    logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.INFO)
    logging.info("Searching for movie and subtitle files to be merged")
    try:
        run(sys.argv[1:])
    except RuntimeError as e:
        logging.error(f"Unexpected error occured: {e}. Terminating")
        exit(1)

    logging.info("Done")
