
import argparse
import glob
import logging
import os
import shutil
import sys
import tempfile
from tqdm import tqdm
from tqdm.contrib.logging import logging_redirect_tqdm
from pathlib import Path
from typing import Dict, List, Tuple

from . import utils


work = True


class Merge(utils.InterruptibleProcess):

    def __init__(self, dry_run: bool, language: str, lang_priority: str):
        super().__init__()
        self.dry_run = dry_run
        self.language = language
        self.lang_priority = [] if not lang_priority or lang_priority == "" else lang_priority.split(",")

    def _build_subtitle_from_path(self, path: str) -> utils.SubtitleFile:
        language = None if self.language == "auto" else self.language

        return utils.build_subtitle_from_path(path, language)

    def _directory_subtitle_matcher(self, dir_path: str) -> Dict[str, List[utils.SubtitleFile]]:
        """
            Match subtitles to videos found in 'path' directory
        """
        videos = []
        subtitles = []

        matches = {}

        with os.scandir(dir_path) as it:
            for entry in it:
                if entry.is_file():
                    path = entry.path
                    if utils.is_video(path):
                        videos.append(path)
                    elif utils.is_subtitle(path):
                        subtitles.append(path)

        # sort both lists by lenght
        videos = sorted(videos, reverse = True, key = lambda k: len(k))
        subtitles = sorted(subtitles, reverse = True, key = lambda k: len(k))

        for video in videos:
            video_parts = utils.split_path(video)
            video_file_name = video_parts[1]

            matching_subtitles = []
            for subtitle in subtitles:
                subtitle_parts = utils.split_path(subtitle)
                subtitle_file_name = subtitle_parts[1]

                if subtitle_file_name.startswith(video_file_name):
                    matching_subtitles.append(subtitle)

            for subtitle in matching_subtitles:
                subtitles.remove(subtitle)

            if matching_subtitles:
                matches[video] = [self._build_subtitle_from_path(subtitle) for subtitle in matching_subtitles]

        if len(subtitles) > 0:
            subtitles_str = '\n'.join(subtitles)
            logging.warning(f"When matching videos with subtitles in {path}, given subtitles were not matched to any video: {subtitles_str}")

        return matches


    def _recursive_subtitle_search(self, path: str) -> [utils.SubtitleFile]:
        found_subtitles = []
        found_subdirs = []

        with os.scandir(path) as it:
            for entry in it:
                if entry.is_dir():
                    found_subdirs.append(entry.path)
                elif entry.is_file():
                    if utils.is_video(entry.path):
                        # if there is a video file then all possible subtitles at this level (and below) belong to
                        # it, quit recursion for current directory
                        return []
                    elif utils.is_subtitle(entry.path):
                        found_subtitles.append(entry.path)

        # if we got here, then no video was found at this level
        subtitles = [self._build_subtitle_from_path(subtitle) for subtitle in found_subtitles]

        for subdir in found_subdirs:
            sub_subtitles = self._recursive_subtitle_search(subdir)
            subtitles.extend(subtitles)

        return subtitles

    def _aggressive_subtitle_search(self, path: str) -> [utils.SubtitleFile]:
        """
            Function collects all subtitles in video dir and from all subdirs
        """
        subtitles = []
        directory = Path(path).parent

        for entry in os.scandir(directory):
            if entry.is_dir():
                sub_subtitles = self._recursive_subtitle_search(entry.path)
                subtitles.extend(sub_subtitles)
            elif entry.is_file() and utils.is_subtitle(entry.path):
                subtitle = self._build_subtitle_from_path(entry.path)
                subtitles.append(subtitle)

        return subtitles

    @staticmethod
    def _get_index_for(l: [], value):
        try:
            return l.index(value)
        except ValueError:
            return len(l)

    def _sort_subtitles(self, subtitles: [utils.SubtitleFile]) -> [utils.SubtitleFile]:
        priorities = self.lang_priority.copy()
        priorities.append(None)
        subtitles_sorted = sorted(subtitles, key=lambda s: self._get_index_for(priorities, s.language))

        return subtitles_sorted

    def _convert_subtitle(self, video_fps: str, subtitle: utils.SubtitleFile, temporary_dir: str) -> [utils.SubtitleFile]:
        converted_subtitle = subtitle

        if not self.dry_run:
            input_file = subtitle.path
            output_file = utils.get_unique_file_name(temporary_dir, "srt")
            encoding = subtitle.encoding if subtitle.encoding != "UTF-8-SIG" else "utf-8"

            status = utils.start_process("ffmpeg",
                                         ["-hide_banner", "-y", "-sub_charenc", encoding, "-i", input_file, output_file])

            if status.returncode == 0:
                # there is no way (as of now) to tell ffmpeg to convert subtitles with proper frame rate in mind.
                # so here some naive conversion is being done
                # see: https://trac.ffmpeg.org/ticket/10929
                #      https://trac.ffmpeg.org/ticket/3287
                if utils.is_subtitle_microdvd(subtitle):
                    fps = eval(video_fps)

                    # prepare new output file, and use previous one as new input
                    input_file = output_file
                    output_file = utils.get_unique_file_name(temporary_dir, "srt")

                    utils.fix_subtitles_fps(input_file, output_file, fps)

            else:
                raise RuntimeError(f"ffmpeg exited with unexpected error:\n{status.stderr}")

            converted_subtitle = utils.SubtitleFile(output_file, subtitle.language, "utf-8")

        return converted_subtitle

    def _merge(self, input_video: str, subtitles: [utils.SubtitleFile]):
        logging.info(f"Merging video file: {input_video} with subtitles:")

        video_dir, video_name, video_extension = utils.split_path(input_video)
        output_video = video_dir + "/" + video_name + "." + "mkv"
        temporary_output_video = video_dir + "/_tt_merge_" + video_name + "." + "mkv"

        # collect details about input file
        input_file_details = utils.get_video_data(input_video)

        input_files = []

        # register input for removal
        input_files.append(input_video)

        # set subtitles and languages
        sorted_subtitles = self._sort_subtitles(subtitles)
        sorted_subtitles_str = ", ".join([subtitle.language if subtitle.language is not None else "unknown" for subtitle in sorted_subtitles])

        with tempfile.TemporaryDirectory() as temporary_subtitles_dir:
            prepared_subtitles = []
            for subtitle in sorted_subtitles:
                logging.info(f"\t[{subtitle.language}]: {subtitle.path}")
                input_files.append(subtitle.path)

                # Subtitles are buggy sometimes, use ffmpeg to fix them.
                # Also makemkv does not handle MicroDVD subtitles, so convert all to SubRip.
                fps = input_file_details.video_tracks[0].fps
                converted_subtitle = self._convert_subtitle(fps, subtitle, temporary_subtitles_dir)

                prepared_subtitles.append(converted_subtitle)

            # perform
            logging.debug("\tMerge in progress...")
            if not self.dry_run:
                utils.generate_mkv(input_video=input_video, output_path=temporary_output_video, subtitles=prepared_subtitles)

                # Remove all inputs
                for input in input_files:
                    os.remove(input)

                # rename final file to a proper one
                shutil.move(temporary_output_video, output_video)

        logging.debug("\tDone")

    def _process_single_video(self, video_file: str) -> Tuple[str, List[utils.SubtitleFile]]:
        logging.debug(f"Analyzing subtitles for a single video: {video_file}")
        subtitles = self._aggressive_subtitle_search(video_file)

        if len(subtitles) == 0:
            return None
        else:
            return (video_file, subtitles)

    def _process_dir_with_many_videos(self, dir_path: str) -> Dict[str, List[utils.SubtitleFile]]:
        """
            Function launches matching for videos in subtitles in directory with many videos
        """
        logging.debug(f"Analyzing subtitles for videos in: {dir_path}")
        return self._directory_subtitle_matcher(dir_path)


    def _process_dir(self, path: str) -> Dict[str, List[utils.SubtitleFile]]:
        logging.debug(f"Finding videos in {path}")
        videos_and_subtitles = {}

        for cd, _, files in os.walk(path, followlinks = True):
            video_files = []
            for file in files:
                self._check_for_stop()
                file_path = os.path.join(cd, file)

                if utils.is_video(file_path):
                    video_files.append(file_path)

            # check if number of unique file names (excluding extensions) is equal to number of files (including extensions).
            # if no, then it means there are at least two video files with the same name but different extension.
            # this is a cumbersome situation so just don't allow it
            unique_names = set(Path(video).stem for video in video_files)
            if len(unique_names) != len(video_files):
                logging.warning(f"Two video files with the same name found in {cd}. This is not supported, skipping whole directory.")
                continue

            videos = len(video_files)
            if videos == 1:
                video_and_subtitles = self._process_single_video(video_files[0])

                if video_and_subtitles is not None:
                    (video, subtitles) = video_and_subtitles
                    videos_and_subtitles[video] = subtitles
            elif videos > 1:
                matching_videos_and_subtitles = self._process_dir_with_many_videos(cd)

                videos_and_subtitles.update(matching_videos_and_subtitles)

        return videos_and_subtitles


    def process_dir(self, path: str):
        logging.info(f"Looking for video and subtitle files in {path}")
        vas = self._process_dir(path)

        logging.info(f"Found {len(vas)} videos with subtitles to merge")
        for video in vas:
            logging.debug(video)

        logging.info("Starting merge")
        with logging_redirect_tqdm():
            for video, subtitles in tqdm(vas.items(), desc="Merging", unit="video", leave=False, smoothing=0.1, mininterval=.2, disable=utils.hide_progressbar()):
                self._check_for_stop()
                self._merge(video, subtitles)


def setup_parser(parser: argparse.ArgumentParser):
    parser.add_argument('videos_path',
                        nargs=1,
                        help='Path with videos to combine.')
    parser.add_argument("--language", "-l",
                        help='Language code for found subtitles. By default none is used. See mkvmerge '
                             '--list-languages for available languages. For automatic detection use: auto')
    parser.add_argument("--languages-priority", "-p",
                        help='Comma separated list of two letter language codes. Order on the list defines order of '
                             'subtitles appending.\nFor example, for --languages-priority pl,de,en,fr all '
                             'found subtitles will be ordered so polish goes as first, then german, english and '
                             'french. If there are subtitles in any other language, they will be append at '
                             'the end in undefined order')


def run(args):
    for tool in ["mkvmerge", "ffmpeg", "ffprobe"]:
        path = shutil.which(tool)
        if path is None:
            raise RuntimeError(f"{tool} not found in PATH")
        else:
            logging.debug(f"{tool} path: {path}")

    logging.info("Searching for movie and subtitle files to be merged")
    two_tone = Merge(dry_run=not args.no_dry_run,
                       language=args.language,
                       lang_priority=args.languages_priority)
    two_tone.process_dir(args.videos_path[0])
