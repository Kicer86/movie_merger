
import argparse
import logging
import re
from collections import defaultdict

from . import utils


class Concatenate(utils.InterruptibleProcess):
    def __init__(self, live_run: bool):
        super().__init__()

        self.live_run = live_run

    def run(self, path: str):
        logging.info(f"Collecting video files from path {path}")
        video_files = utils.collect_video_files(path, self)

        logging.info("Finding splitted videos")
        parts_regex = re.compile("(.*[^0-9a-z]+)(cd\\d+)([^0-9a-z]+.*)", re.IGNORECASE)
        splitted = [video_file for video_file in video_files if parts_regex.match(video_file)]

        logging.info("Matching videos")
        matched_videos = defaultdict(list)
        for video in splitted:
            match = parts_regex.search(video)
            name_without_part_number = match.group(1)[:-1] + match.group(3)                                     # remove last char before CDXXX as it is most likely space or hyphen
            matched_videos[name_without_part_number].append((match.group(1), match.group(2), match.group(3)))

        logging.info("Processing groups")
        warnings = False
        for common_name, segments in matched_videos.items():
            parts = []
            for segment in segments:
                part = segment[1]       # cdXXX
                partNo = part[2:]       # XXX
                parts.append(int(partNo))

            # expect parts to be numbered from 1 to N
            parts.sort()

            for i, value in enumerate(parts):
                if i + 1 != value:
                    logging.warning(f"There is a mismatch in CD numbers for a group of files represented under a common name: {common_name}")
                    warnings = True

        if warnings:
            logging.error("Fix above warnings and try again")
            return


def setup_parser(parser: argparse.ArgumentParser):
    parser.description = (
        "Concatenate is a tool for concatenating video files splitted into many files into one.\n"
        "For example if you have movie consisting of two files: movie-cd1.avi and movie-cd2.avi\n"
        "then 'concatenate' tool will glue them into one file 'movie.avi'.\n"
        "If your files come with subtitle files, you may want to use 'merge' tool first\n"
        "to merge video files with corresponding subtitle files.\n"
        "Otherwise you will end up with one video file and two subtitle files for cd1 and cd2 which will be useless now"
    )
    parser.add_argument('videos_path',
                        nargs=1,
                        help='Path with videos to concatenate.')


def run(args):
    concatenate = Concatenate(args.no_dry_run)
    concatenate.run(args.videos_path[0])
