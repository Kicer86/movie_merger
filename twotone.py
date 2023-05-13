
import argparse
import langid
import logging
import os
import signal
import subprocess
import sys
import tempfile
from collections import namedtuple
from pathlib import Path

import utils


Subtitle = namedtuple("Subtitle", "path language encoding")
work = True


class TwoTone:

    def __init__(self, dry_run: bool, language: str, lang_priority: str):
        self.dry_run = dry_run
        self.language = language
        self.to_be_removed = []
        self.lang_priority = [] if not lang_priority or lang_priority == "" else lang_priority.split(",")

    def _remove_later(self, path: str):
        self.to_be_removed.append(path)

    def _remove(self):
        for file_to_remove in self.to_be_removed:
            os.remove(file_to_remove)
        self.to_be_removed.clear()

    def _split_path(self, path: str) -> (str, str, str):
        info = Path(path)

        return str(info.parent), info.stem, info.suffix[1:]

    def _build_subtitle_from_path(self, path: str) -> Subtitle:
        encoding = utils.file_encoding(path)
        language = self.language if self.language != "auto" else self._guess_language(path, encoding)

        return Subtitle(path, language, encoding)

    def _simple_subtitle_search(self, path: str) ->[Subtitle]:
        video_name = Path(path).stem
        dir = Path(path).parent

        subtitles = []

        for subtitle_ext in ["txt", "srt"]:
            subtitle_file = video_name + "." + subtitle_ext
            subtitle_path = os.path.join(dir, subtitle_file)
            if os.path.exists(subtitle_path) and utils.is_subtitle(subtitle_path):
                subtitle = self._build_subtitle_from_path(subtitle_path)
                subtitles.append(subtitle)

        return subtitles

    def _aggressive_subtitle_search(self, path: str) -> [Subtitle]:
        subtitles = self._simple_subtitle_search(path)
        dir = Path(path).parent

        for entry in os.scandir(dir):
            if entry.is_file() and utils.is_subtitle(entry.path):
                subtitle = self._build_subtitle_from_path(entry.path)
                subtitles.append(subtitle)

        return list(set(subtitles))

    def _get_index_for(self, l: [], value):
        try:
            return l.index(value)
        except ValueError:
            return len(l)

    def _sort_subtitles(self, subtitles: [Subtitle]) -> [Subtitle]:
        priorities = self.lang_priority.copy()
        priorities.append(None)
        subtitles_sorted = sorted(subtitles, key = lambda s: self._get_index_for(priorities, s.language))

        return subtitles_sorted

    def _convert_subtitle(self, subtitle: Subtitle) -> [Subtitle]:
        converted_subtitle = subtitle

        if self.dry_run == False:
            output_file = tempfile.NamedTemporaryFile()
            output_subtitle = output_file.name + ".srt"

            status = subprocess.run(["ffmpeg", "-sub_charenc", subtitle.encoding, "-i", subtitle.path, output_subtitle], capture_output = True)

            output_file.close()

            if status.returncode != 0:
                raise RuntimeError(f"ffmpeg exited with unexpected error:\n{status.stderr.decode('utf-8')}")

            converted_subtitle = Subtitle(output_subtitle, subtitle.language, subtitle.encoding)

        return converted_subtitle

    def _guess_language(self, path: str, encoding: str) -> str:
        result = ""

        with open(path, "r", encoding = encoding) as sf:
            content = sf.readlines()
            content_joined = "".join(content)
            result = langid.classify(content_joined)[0]

        return result

    def _run_mkvmerge(self, options: [str]):
        if not self.dry_run:
            process = ["mkvmerge"]
            process.extend(options)
            result = subprocess.run(process, capture_output = True)

            logging.debug(result.stdout.decode("utf-8") )

            if result.returncode != 0:
                raise RuntimeError(f"mkvmerge exited with unexpected error:\n{result.stdout.decode('utf-8')}")

    def _merge(self, input_video: str, subtitles: [str]):
        logging.info(f"Video file: {input_video}")

        video_dir, video_name, video_extension = self._split_path(input_video)
        tmp_video = video_dir + "/." + video_name + "." + "mkv"
        output_video = video_dir + "/" + video_name + "." + "mkv"

        options = ["-o", tmp_video, input_video]

        self._remove_later(input_video)

        sorted_subtitles = self._sort_subtitles(subtitles)

        for subtitle in sorted_subtitles:
            lang = subtitle.language
            if lang and lang != "":
                options.append("--language")
                options.append("0:" + lang)

            converted_subtitle = self._convert_subtitle(subtitle)       # subtitles are buggy sometimes, ffmpeg fixes them
            self._remove_later(converted_subtitle.path)
            if converted_subtitle.path != subtitle.path:
                self._remove_later(subtitle.path)

            options.append(converted_subtitle.path)

            logging.info(f"\tadd subtitles [{lang}]: {subtitle.path}")

        logging.debug(f"\tStarting mkvmerge with options:{options}")
        logging.info("\tMerge in progress...")
        self._run_mkvmerge(options)

        if not self.dry_run and os.path.exists(tmp_video):
            self._remove()
            os.rename(tmp_video, output_video)

    def _process_video(self, video_file: str, subtitles_fetcher):
        subtitles = subtitles_fetcher(video_file)
        if subtitles:
            self._merge(video_file, subtitles)

    def process_dir(self, path: str):
        global work
        if not work:
            return

        video_files = []
        for entry in os.scandir(path):
            if entry.is_file() and utils.is_video(entry.path):
                video_files.append(entry.path)
            elif entry.is_dir():
                self.process_dir(entry.path)

        if len(video_files) == 1:
            self._process_video(video_files[0], self._aggressive_subtitle_search)
        if len(video_files) > 1:
            for video_file in video_files:
                self._process_video(video_file, self._simple_subtitle_search)


def run(sys_args: [str]):
    parser = argparse.ArgumentParser(description='Combine many video/subtitle files into one mkv file. Try dry run before running as ALL source files will be deleted. ' \
        'It is safe to stop this script with ctrl+c - it will quit gracefully in a while.')
    parser.add_argument('videos_path',
                        nargs = 1,
                        help = 'Path with videos to combine.')
    parser.add_argument("--dry-run", "-n",
                        action = 'store_true',
                        default = False,
                        help = 'No not modify any file, just print what will happen.')
    parser.add_argument("--language", "-l",
                        help = 'Language code for found subtitles. By default none is used. See mkvmerge --list-languages for available languages. For automatic detection use: auto')
    parser.add_argument("--languages-priority", "-p",
                        help = 'Comma separated list of two letter language codes. Order on the list defines order of subtitles appending.\nFor example, for --languages-priority pl,de,en,fr all '\
                               'found subtitles will be ordered so polish goes as first, then german, english and french. If there are subtitles in any other language, they will be append at '\
                               'the end in undefined order')
    parser.add_argument("--verbose", action = 'store_true', default = False, help = 'Verbose output')

    args = parser.parse_args(sys_args)

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    two_tone = TwoTone(dry_run = args.dry_run,
                       language = args.language,
                       lang_priority = args.languages_priority)
    two_tone.process_dir(args.videos_path[0])



def term_handler(signum, frame):
    global work
    logging.warning("SIGTERM received, stopping soon")
    work = False


if __name__ == '__main__':
    signal.signal(signal.SIGINT, term_handler)
    logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.INFO)
    logging.info("Searching for movie and subtitle files to be merged")
    try:
        run(sys.argv[1:])
    except RuntimeError as e:
        logging.error(f"Unexpected error occured: {e}. Terminating")
        exit(1)

    if work:
        logging.info("Done")
    else:
        logging.warning("Quitted due to SIGTERM")
