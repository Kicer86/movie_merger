
import cchardet
import json
import logging
import math
import os.path
import re
import subprocess
from collections import namedtuple
from itertools import islice
from pathlib import Path

SubtitleFile = namedtuple("Subtitle", "path language encoding")
Subtitle = namedtuple("Subtitle", "language default length tid format")
VideoTrack = namedtuple("VideoTrack", "fps length")
VideoInfo = namedtuple("VideoInfo", "video_tracks subtitles path")
ProcessResult = namedtuple("ProcessResult", "returncode stdout stderr")

subtitle_format1 = re.compile("[0-9]{2}:[0-9]{2}:[0-9]{2}:.*")
subtitle_format2 = re.compile("(?:0|1)\n[0-9]{2}:[0-9]{2}:[0-9]{2},[0-9]{3} --> [0-9]{2}:[0-9]{2}:[0-9]{2},[0-9]{3}\n", flags = re.MULTILINE)
microdvd_time_pattern = re.compile("\\{[0-9]+\\}\\{[0-9]+\\}.*")
subrip_time_pattern = re.compile(r'(\d+:\d{2}:\d{2},\d{3}) --> (\d+:\d{2}:\d{2},\d{3})')

ffmpeg_default_fps = 23.976                      # constant taken from https://trac.ffmpeg.org/ticket/3287


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

                for subtitle_format in [subtitle_format1, microdvd_time_pattern, subtitle_format2]:
                    if subtitle_format.match(head):
                        logging.debug("\tSubtitle format detected")
                        return True

    logging.debug("\tNot a subtitle file")
    return False


def is_subtitle_microdvd(subtitle: Subtitle) -> bool:
    with open(subtitle.path, 'r', encoding = subtitle.encoding) as text_file:
        head = "".join(islice(text_file, 5)).strip()

        if microdvd_time_pattern.match(head):
            return True

    return False


def time_to_ms(time_str: str) -> int:
    """ Convert time string 'HH:MM:SS,SSS' to milliseconds """
    h, m, s, ms = re.split(r'[:.,]', time_str)
    return (int(h) * 3600 + int(m) * 60 + int(s)) * 1000 + int(ms[:3])


def time_to_s(time: str):
    return time_to_ms(time) / 1000


def ms_to_time(ms: int) -> str:
    """ Convert milliseconds to time string 'HH:MM:SS,SSS' """
    h, remainder = divmod(ms, 3600000)
    m, remainder = divmod(remainder, 60000)
    s, ms = divmod(remainder, 1000)
    return f"{int(h):02}:{int(m):02}:{int(s):02},{int(ms):03}"


def fps_str_to_float(fps: str) -> float:
    return eval(fps)


def fix_subtitles_fps(input_path: str, output_path: str, subtitles_fps: float):
    """ fix subtitle's fps """
    scale = subtitles_fps / ffmpeg_default_fps

    if math.isclose(scale, 1, rel_tol = 0.001):         # scale == 1? nothing to fix
        return

    with open(input_path, 'r', encoding='utf-8') as infile, open(output_path, 'w', encoding='utf-8') as outfile:
        for line in infile:
            match = subrip_time_pattern.match(line)
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

def get_video_full_info(path: str) -> str:
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

    return output_json


def get_video_data(path: str) -> [VideoInfo]:

    def get_length(stream):

        length = None

        if "tags" in stream:
            tags = stream["tags"]
            duration = tags.get("DURATION", None)
            if duration is not None:
                length = time_to_ms(duration)

        if length is None:
            length = stream.get("duration", None)
            if length is not None:
                length = float(length)

        return length

    output_json = get_video_full_info(path)

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
            length = get_length(stream)
            tid = stream["index"]
            format = stream["codec_name"]

            subtitles.append(Subtitle(language, default=is_default, length=length, tid=tid, format=format))
        elif stream_type == "video":
            fps = stream["r_frame_rate"]
            length = get_length(stream)

            video_tracks.append(VideoTrack(fps=fps, length=length))

    return VideoInfo(video_tracks, subtitles, path)


def split_path(path: str) -> (str, str, str):
    info = Path(path)

    return str(info.parent), info.stem, info.suffix[1:]


def generate_mkv(input_video: str, output_path: str, subtitles: [SubtitleFile]):
    # output
    options = ["-o", output_path]

    # set input
    options.append(input_video)

    # set subtitles and languages
    for i in range(len(subtitles)):
        subtitle = subtitles[i]
        lang = subtitle.language

        if lang and lang != "":
            options.extend(["--language", f"0:{lang}"])

        if i == 0:
            options.extend(["--default-track", "0:yes"])
        else:
            options.extend(["--default-track", "0:no"])

        options.append(subtitle.path)

    # perform
    cmd = "mkvmerge"
    result = start_process(cmd, options)

    if result.returncode != 0:
        if os.path.exists(output_path):
            os.remove(output_path)
        raise RuntimeError(f"{cmd} exited with unexpected error:\n{result.stderr.decode('utf-8')}")

    if not os.path.exists(output_path):
        logging.error("Output file was not created")
        raise RuntimeError(f"{cmd} did not create output file")

    # validate output file correctness
    output_file_details = get_video_data(output_path)
    input_file_details = get_video_data(input_video)

    if not compare_videos(input_file_details.video_tracks, output_file_details.video_tracks) or \
            len(input_file_details.subtitles) + len(subtitles) != len(output_file_details.subtitles):
        logging.error("Output file seems to be corrupted")
        raise RuntimeError("mkvmerge created a corrupted file")


def compare_videos(lhs: [VideoTrack], rhs: [VideoTrack]) -> bool:
    if len(lhs) != len(rhs):
        return False

    for lhs_item, rhs_item in zip(lhs, rhs):
        lhs_fps = fps_str_to_float(lhs_item.fps)
        rhs_fps = fps_str_to_float(rhs_item.fps)

        if lhs_fps == rhs_fps:
            return True

        diff = abs(lhs_fps - rhs_fps)

        # For videos with fps 1000000/33333 (≈30fps) mkvmerge generates video with 30/1 fps.
        # I'm not sure if this is acceptable but at this moment let it be
        if diff > 0.0005:
            return False

    return True
