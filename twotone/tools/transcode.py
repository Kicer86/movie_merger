
import argparse
import logging
import os
import random
import re
import shutil
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from tqdm import tqdm
from tqdm.contrib.logging import logging_redirect_tqdm

from . import utils

class Transcoder(utils.InterruptibleProcess):
    def __init__(self, live_run: bool = False, target_ssim: float = 0.98, codec: str = "libx265"):
        super().__init__()
        self.live_run = live_run
        self.target_ssim = target_ssim
        self.codec = codec


    def _find_video_files(self, directory):
        """Find video files with specified extensions."""
        video_files = []
        for root, _, files in os.walk(directory):
            for file in files:
                if utils.is_video(file):
                    video_files.append(os.path.join(root, file))
        return video_files


    def _calculate_quality(self, original, transcoded):
        """Calculate SSIM between original and transcoded video."""
        args = [
            "-i", original, "-i", transcoded,
            "-lavfi", "ssim", "-f", "null", "-"
        ]

        result = utils.start_process("ffmpeg", args)
        ssim_line = [line for line in result.stderr.splitlines() if "All:" in line]

        if ssim_line:
            # Extract the SSIM value immediately after "All:"
            ssim_value = ssim_line[-1].split("All:")[1].split()[0]
            try:
                return float(ssim_value)
            except ValueError:
                logging.error(f"Failed to parse SSIM value: {ssim_value}")
                return None

        return None


    def _transcode_video(self, input_file, output_file, crf, preset, input_params=[], output_params=[], audio_codec=["-an"], show_progress=False):
        """
        Encode video with a given CRF, preset, and extra parameters.
        By default audio is removed as in most cases this function is being used
        for finding optimal CRF and quite often audio may alter SSIM results
        (in most cases due to interfering with timestamps).
        """

        args = [
            "-v", "error", "-stats", "-nostdin",
            *input_params,
            "-i", input_file,
            "-c:v", self.codec,
            "-crf", str(crf),
            "-preset", preset,
            "-profile:v", "main10",
            *audio_codec,
            *output_params,
            output_file
        ]

        utils.raise_on_error(utils.start_process("ffmpeg", args, show_progress=show_progress))


    def _extract_segment(self, video_file, start_time, end_time, output_file):
        """ Extract video segment. Video is transcoded with lossless quality to rebuild damaged or troublesome videos """
        self._transcode_video(
            video_file,
            output_file,
            crf=0,
            preset="veryfast",
            input_params=["-ss", str(start_time), "-to", str(end_time)]
        )


    def _extract_segments(self, video_file: str, segments, output_dir: str):
        output_files = []
        _, filename, ext = utils.split_path(video_file)

        i = 0
        with logging_redirect_tqdm():
            for (start, end) in tqdm(segments, desc="Extracting scenes", unit="scene", leave=False, smoothing=0.1, mininterval=.2, disable=utils.hide_progressbar()):
                self._check_for_stop()
                output_file = os.path.join(output_dir, f"{filename}.frag{i}.{ext}")
                self._extract_segment(video_file, start, end, output_file)
                output_files.append(output_file)
                i += 1

        return output_files


    def _select_scenes(self, video_file, segment_duration=5):
        """
        Select video segments around detected scene changes, merging nearby timestamps.

        Parameters:
            video_file (str): Path to the input video file.
            segment_duration (int): Minimum duration (in seconds) of each segment.

        Returns:
            list: Full paths to the generated video files.
        """

        # FFmpeg command to detect scene changes and log timestamps
        args = [
            "-i", video_file,
            "-vf", "select='gt(scene,0.6)',showinfo",
            "-vsync", "vfr", "-f", "null", "/dev/null"
        ]

        result = utils.start_process("ffmpeg", args)

        # Parse timestamps from the ffmpeg output
        timestamps = []
        showinfo_output = result.stderr
        for line in showinfo_output.splitlines():
            match = re.search(r"pts_time:(\d+(\.\d+)?)", line)
            if match:
                timestamps.append(float(match.group(1)))

        # Generate segments with padding
        segments = []
        for timestamp in timestamps:
            start = max(0, timestamp - segment_duration / 2)
            end = timestamp + segment_duration / 2
            segments.append((start, end))

        # # Merge overlapping segments
        merged_segments = []
        for start, end in sorted(segments):
            if not merged_segments or start > merged_segments[-1][1]:  # No overlap
                merged_segments.append((start, end))
            else:  # Overlap detected, merge
                merged_segments[-1] = (merged_segments[-1][0], max(merged_segments[-1][1], end))

        return merged_segments


    def _select_segments(self, video_file, segment_duration=5):
        duration = utils.get_video_duration(video_file) / 1000
        num_segments = max(3, min(10, int(duration // 30)))

        if duration <= 0 or num_segments <= 0 or segment_duration <= 0:
            raise ValueError("Total length, number of segments, and segment length must all be positive.")
        if segment_duration > duration:
            raise ValueError("Segment length cannot exceed total length.")
        if num_segments * segment_duration > duration:
            raise ValueError("Total segments cannot fit within the total length.")

        step = (duration - segment_duration) / (num_segments - 1) if num_segments > 1 else 0

        segments = [(round(i * step), round(i * step) + segment_duration) for i in range(num_segments)]

        return segments


    def _bisection_search(self, eval_func, min_value, max_value, target_condition):
        """
        Generic bisection search algorithm.

        Parameters:
            eval_func (callable): Function to evaluate the current value (e.g., CRF).
                                Should return a tuple (value, evaluation_result).
            min_value (int): Minimum value of the range to search.
            max_value (int): Maximum value of the range to search.
            target_condition (callable): Function to check if the evaluation result meets the desired condition.
                                        Should return True if the condition is met.

        Returns:
            Tuple[int, any]: The optimal value and its corresponding evaluation result.
        """
        best_value = None
        best_result = None

        while min_value <= max_value:
            mid_value = (min_value + max_value) // 2
            eval_result = eval_func(mid_value)

            if eval_result is not None and target_condition(eval_result):
                best_value = mid_value
                best_result = eval_result
                min_value = mid_value + 1
            else:
                max_value = mid_value - 1

        return best_value, best_result


    def _transcode_segment_and_compare(self, wd_dir: str, segment_file: str, crf: int) -> float or None:
        _, filename, ext = utils.split_path(segment_file)

        transcoded_segment_output = os.path.join(wd_dir, f"{filename}.transcoded.{ext}")

        self._transcode_video(segment_file, transcoded_segment_output, crf, "veryfast", output_params = ["-vsync", "vfr"])

        quality = self._calculate_quality(segment_file, transcoded_segment_output)
        return quality

    def _for_segments(self, segments, op, title, unit):
        with logging_redirect_tqdm(), \
             tqdm(desc=title, unit=unit, total=len(segments), **utils.get_tqdm_defaults()) as pbar, \
             tempfile.TemporaryDirectory() as wd_dir, \
             ThreadPoolExecutor() as executor:
            def worker(file_path):
                op(wd_dir, file_path)
                pbar.update(1)

            for segment in segments:
                executor.submit(worker, segment)

    def _final_transcode(self, input_file, crf):
        """Perform the final transcoding with the best CRF using the determined extra_params."""
        _, basename, ext = utils.split_path(input_file)

        logging.info(f"Starting final transcoding with CRF: {crf}")
        final_output_file = f"{basename}.temp.{ext}"
        self._transcode_video(input_file, final_output_file, crf, "veryslow", audio_codec=["-c:a", "copy"], output_params = ["-vsync", "passthrough"], show_progress=True)

        original_size = os.path.getsize(input_file)
        final_size = os.path.getsize(final_output_file)
        size_reduction = (final_size / original_size) * 100

        # Measure SSIM again after final transcoding
        final_quality = self._calculate_quality(input_file, final_output_file)

        try:
            if final_quality < self.target_ssim:
                logging.warning(
                    f"Final CRF: {crf}, SSIM: {final_quality}. "
                    f"Final transcode resulted in lower SSIM than requested: {final_quality} < {self.target_ssim}"
                )
                raise ValueError()

            if final_size > original_size:
                logging.warning(
                    f"Final CRF: {crf}, SSIM: {final_quality}. "
                    f"Encoded file is larger than the original. Keeping the original file."
                )
                raise ValueError()


            utils.start_process("exiftool", ["-overwrite_original", "-TagsFromFile", input_file, "-all:all>all:all", final_output_file])

            try:
                os.replace(final_output_file, input_file)
            except OSError:
                shutil.move(final_output_file, input_file)

            logging.info(
                f"Final CRF: {crf}, SSIM: {final_quality}, "
                f"encoded Size: {final_size} bytes, "
                f"size reduced by: {original_size - final_size} bytes "
                f"({size_reduction:.2f}% of original size)"
            )

        except ValueError:
            os.remove(final_output_file)



    def find_optimal_crf(self, input_file, allow_segments=True):
        """Find the optimal CRF using bisection."""
        original_size = os.path.getsize(input_file)

        duration = utils.get_video_duration(input_file)
        if not duration:
            return None

        # convert to seconds
        duration /= 1000

        with tempfile.TemporaryDirectory() as wd_dir:
            segment_files = []
            if allow_segments and duration > 30:
                logging.info(f"Picking segments from {input_file}")
                segments = self._select_scenes(input_file)
                if len(segments) < 2:
                    segments = self._select_segments(input_file)

                segment_files = self._extract_segments(
                    input_file, segments, wd_dir)

                logging.info(f"Starting CRF bisection for {input_file} "
                             f"with veryfast preset using {len(segment_files)} segments")
            else:
                segment_files = [input_file]
                logging.info(f"Starting CRF bisection for {input_file} with veryfast preset using whole file")

            def evaluate_crf(mid_crf):
                self._check_for_stop()
                qualities = []

                def get_quality(wd_dir, segment_file):
                    quality = self._transcode_segment_and_compare(wd_dir, segment_file, mid_crf)
                    if quality:
                        qualities.append(quality)

                self._for_segments(segment_files, get_quality, "SSIM calculation", "scene")

                avg_quality = sum(qualities) / len(qualities) if qualities else 0
                logging.info(f"CRF: {mid_crf}, Average Quality (SSIM): {avg_quality}")

                return avg_quality

            top_quality = evaluate_crf(0)
            if top_quality < 0.9975:
                raise RuntimeError(f"Sanity check failed: top SSIM value: {top_quality} < 0.9975")

            if top_quality < self.target_ssim:
                raise RuntimeError(f"Top SSIM value: {top_quality} < requested SSIM: {self.target_ssim}")

            crf_min, crf_max = 0, 51
            best_crf, best_quality = self._bisection_search(evaluate_crf, min_value = crf_min, max_value = crf_max, target_condition=lambda avg_quality: avg_quality >= self.target_ssim)

            if best_crf is not None and best_quality is not None:
                logging.info(f"Finished CRF bisection. Optimal CRF: {best_crf} with quality: {best_quality}")
            else:
                logging.warning(f"Finished CRF bisection. Could not find CRF matching desired quality ({self.target_ssim}).")
            return best_crf


    def transcode(self, directory: str):
        logging.info(f"Starting video transcoding with {self.codec}. Target SSIM: {self.target_ssim}")
        video_files = self._find_video_files(directory)

        for file in video_files:
            self._check_for_stop()
            logging.info(f"Processing {file}")
            best_crf = self.find_optimal_crf(file)
            if best_crf is not None and self.live_run:
                # increase crf by one as veryslow preset will be used, so result should be above requested quality anyway
                self._final_transcode(file, best_crf + 1)
            elif not self.live_run:
                logging.info(f"Dry run. Skipping final transcoding step.")

            logging.info(f"Finished processing {file}")

        logging.info("Video processing completed")


def setup_parser(parser: argparse.ArgumentParser):
    def valid_ssim_value(value):
        try:
            fvalue = float(value)
            if 0 <= fvalue <= 1:
                return fvalue
            else:
                raise argparse.ArgumentTypeError(f"SSIM value must be between 0 and 1. Got {value}")
        except ValueError:
            raise argparse.ArgumentTypeError(f"Invalid SSIM value: {value}")

    parser.add_argument("--ssim", "-s",
                        type=valid_ssim_value,
                        default=0.98,
                        help='Requested SSIM value (video quality). Valid values are between 0 and 1.')
    parser.add_argument('videos_path',
                        nargs=1,
                        help='Path with videos to transcode.')


def run(args):
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    transcoder = Transcoder(live_run = args.no_dry_run, target_ssim = args.ssim)
    transcoder.transcode(args.videos_path[0])
