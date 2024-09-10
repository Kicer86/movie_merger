
import cchardet
import json
import logging
import os.path
import re
import subprocess
from collections import namedtuple
from itertools import islice
from pathlib import Path

Subtitle = namedtuple("Subtitle", "language default")
VideoTrack = namedtuple("VideoTrack", "fps")
VideoInfo = namedtuple("VideoInfo", "video_tracks subtitles")
ProcessResult = namedtuple("ProcessResult", "returncode stdout stderr")

subtitle_format1 = re.compile("[0-9]{2}:[0-9]{2}:[0-9]{2}:.*")
subtitle_format2 = re.compile("\\{[0-9]+\\}\\{[0-9]+\\}.*")
subtitle_format3 = re.compile("(?:0|1)\n[0-9]{2}:[0-9]{2}:[0-9]{2},[0-9]{3} --> [0-9]{2}:[0-9]{2}:[0-9]{2},[0-9]{3}\n", flags = re.MULTILINE)


def start_process(process: str, args: [str]) -> ProcessResult:
    command = [process]
    command.extend(args)

    logging.debug(f"Starting {process} with options: {' '.join(args)}")
    sub_process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, preexec_fn=os.setsid)
    stdout, stderr = sub_process.communicate()

    logging.debug(f"Process finished with {sub_process.returncode}")

    return ProcessResult(sub_process.returncode, stdout, stderr)


def file_encoding(file: str) -> str:
    detector = cchardet.UniversalDetector()

    with open(file, 'rb') as file:
        for line in file.readlines():
            detector.feed(line)
            if detector.done:
                break
        detector.close()

    encoding = detector.result["encoding"]

    return encoding


def is_video(file: str) -> bool:
    return Path(file).suffix[1:].lower() in ["mkv", "mp4", "avi", "mpg", "mpeg", "mov"]


def is_subtitle(file: str) -> bool:
    logging.debug(f"Checking file {file} for being subtitle")
    ext = file[-4:]

    if ext == ".srt" or ext == ".sub" or ext == ".txt":
        file = os.path.realpath(file)
        encoding = file_encoding(file)

        if encoding:
            logging.debug(f"\tOpening file with encoding {encoding}")

            with open(file, 'r', encoding = encoding) as text_file:
                head = "".join(islice(text_file, 5)).strip()

                for subtitle_format in [subtitle_format1, subtitle_format2, subtitle_format3]:
                    if subtitle_format.match(head):
                        logging.debug("\tSubtitle format detected")
                        return True

    logging.debug("\tNot a subtitle file")
    return False


def is_subtitle_microdvd(subtitle: Subtitle) -> bool:
    with open(subtitle.path, 'r', encoding = subtitle.encoding) as text_file:
        head = "".join(islice(text_file, 5)).strip()

        if subtitle_format2.match(head):
            return True

    return False


# function fixes subtitle's fps
def fix_subtitles_fps(input_path: str, output_path: str, subtitles_fps: float):
    scale = subtitles_fps / 23.979          # constant chosen empirically

    # Timecode pattern matching
    timecode_pattern = re.compile(r'(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})')

    def time_to_ms(time_str):
        """ Convert time string 'HH:MM:SS,SSS' to milliseconds """
        h, m, s = map(int, time_str[:8].split(':'))
        ms = int(time_str[9:])
        return (h * 3600 + m * 60 + s) * 1000 + ms

    def ms_to_time(ms):
        """ Convert milliseconds to time string 'HH:MM:SS,SSS' """
        h, remainder = divmod(ms, 3600000)
        m, remainder = divmod(remainder, 60000)
        s, ms = divmod(remainder, 1000)
        return f"{h:02}:{m:02}:{s:02},{ms:03}"

    with open(input_path, 'r', encoding='utf-8') as infile, open(output_path, 'w', encoding='utf-8') as outfile:
        for line in infile:
            match = timecode_pattern.match(line)
            if match:
                start_time, end_time = match.groups()
                start_ms = time_to_ms(start_time)
                end_ms = time_to_ms(end_time)

                # Apply scaling
                start_ms = int(start_ms / scale)
                end_ms = int(end_ms / scale)

                # Convert back to time string
                new_start_time = ms_to_time(start_ms)
                new_end_time = ms_to_time(end_ms)

                # Write the updated line
                outfile.write(f"{new_start_time} --> {new_end_time}\n")
            else:
                # Write the line unchanged
                outfile.write(line)


def get_video_data(path: str) -> [VideoInfo]:
    args = []
    args.extend(["-v", "quiet"])
    args.extend(["-print_format", "json"])
    args.append("-show_format")
    args.append("-show_streams")
    args.append(path)

    process = start_process("ffprobe", args)

    if process.returncode != 0:
        raise RuntimeError(f"ffprobe exited with unexpected error:\n{process.stderr.decode('utf-8')}")

    output_lines = process.stdout
    output_str = output_lines.decode('utf8')
    output_json = json.loads(output_lines)

    subtitles = []
    video_tracks = []
    for stream in output_json["streams"]:
        stream_type = stream["codec_type"]
        if stream_type == "subtitle":
            if "tags" in stream:
                tags = stream["tags"]
                language = tags.get("language", None)
            else:
                language = None
            is_default = stream["disposition"]["default"]
            subtitles.append(Subtitle(language, is_default))
        elif stream_type == "video":
            fps = stream["r_frame_rate"]
            video_tracks.append(VideoTrack(fps=fps))

    return VideoInfo(video_tracks, subtitles)


def split_path(path: str) -> (str, str, str):
    info = Path(path)

    return str(info.parent), info.stem, info.suffix[1:]


def compare_videos(lhs: [VideoTrack], rhs: [VideoTrack]) -> bool:
    if len(lhs) != len(rhs):
        return False

    for lhs_item, rhs_item in zip(lhs, rhs):
        lhs_fps = eval(lhs_item.fps)
        rhs_fps = eval(rhs_item.fps)

        if lhs_fps == rhs_fps:
            return True

        diff = abs(lhs_fps - rhs_fps)

        # For videos with fps 1000000/33333 (≈30fps) mkvmerge generates video with 30/1 fps.
        # I'm not sure it this is acceptable but at this moment let it be
        if diff > 0.0005:
            return False

    return True
