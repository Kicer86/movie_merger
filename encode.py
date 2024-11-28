
import os
import logging
import random
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor

import utils


def find_video_files(directory):
    """Find video files with specified extensions."""
    video_files = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.lower().endswith(('.mov', '.mp4', '.mkv')):
                video_files.append(os.path.join(root, file))
    return video_files

def get_video_duration(video_file):
    """Get the duration of a video in seconds."""
    cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", video_file]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, text=True)
    try:
        return float(result.stdout.strip())
    except ValueError:
        logging.error(f"Failed to get duration for {video_file}")
        return None

def select_random_fragments(total_length, num_segments=5, segment_length=5):
    if total_length <= 0 or num_segments <= 0 or segment_length <= 0:
        raise ValueError("Total length, number of segments, and segment length must all be positive.")
    if segment_length > total_length:
        raise ValueError("Segment length cannot exceed total length.")
    if num_segments * segment_length > total_length:
        raise ValueError("Total segments cannot fit within the total length.")

    step = (total_length - segment_length) / (num_segments - 1) if num_segments > 1 else 0
    return [(round(i * step), segment_length) for i in range(num_segments)]

def calculate_quality(original, encoded):
    """Calculate SSIM between original and encoded video."""
    cmd = [
        "ffmpeg", "-i", original, "-i", encoded,
        "-lavfi", "ssim", "-f", "null", "-"
    ]
    result = subprocess.run(cmd, stderr=subprocess.PIPE, text=True)
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

def encode_video(input_file, output_file, crf, preset, extra_params=None):
    """Encode video with a given CRF, preset, and extra parameters."""
    cmd = [
        "ffmpeg", "-v", "error", "-stats", "-nostdin", "-i", input_file,
        "-c:v", "libx265", "-crf", str(crf), "-preset", preset,
        "-profile:v", "main10", "-c:a", "copy", output_file
    ]
    if extra_params:
        cmd.extend(extra_params)

    subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

def extract_fragment(video_file, start_time, fragment_length, output_file):
    status = utils.start_process("ffmpeg",
                        [ "-v", "error", "-stats", "-nostdin",
                          "-fflags", "+genpts",
                          "-ss", str(start_time), "-t", str(fragment_length),
                          "-i", video_file, "-c", "copy", output_file
                        ]
    )

    if status.returncode != 0:
        raise RuntimeError(f"ffmpeg exited with unexpected error:\n{status.stderr.decode('utf-8')}")

def bisection_search(eval_func, min_value, max_value, target_condition):
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


def _encode_segment_and_compare(wd_dir: str, input_file: str, segment: int, start: int, length: int, crf: int) -> float or None:
    _, filename, ext = utils.split_path(input_file)

    encoded_fragment_output = os.path.join(wd_dir, f"{filename}_frag{segment}.enc.{ext}")

    if start is not None and length is not None:
        fragment_output = os.path.join(wd_dir, f"{filename}_frag{segment}.{ext}")
        extract_fragment(input_file, start, length, fragment_output)
    else:
        fragment_output = input_file

    encode_video(fragment_output, encoded_fragment_output, crf, "veryfast")

    quality = calculate_quality(fragment_output, encoded_fragment_output)
    return quality


def _for_segments(segments, op):
    with tempfile.TemporaryDirectory() as wd_dir, ThreadPoolExecutor() as executor:
        def worker(i, start, length):
            op(wd_dir, i, start, length)

        for i, (start, length) in enumerate(segments):
            executor.submit(worker, i, start, length)


def find_optimal_crf(input_file, requested_quality=0.98, allow_segments=True):
    """Find the optimal CRF using bisection."""
    original_size = os.path.getsize(input_file)

    duration = get_video_duration(input_file)
    if not duration:
        return None

    if allow_segments and duration > 30:
        num_fragments = max(3, min(10, int(duration // 30)))
        fragments = select_random_fragments(duration, num_fragments)
        logging.info(f"Starting CRF bisection for {input_file} with veryfast preset using {num_fragments} fragments")
    else:
        fragments = [(None, None)]
        logging.info(f"Starting CRF bisection for {input_file} with veryfast preset using whole file")

    def evaluate_crf(mid_crf):
        qualities = []

        def get_quality(wd_dir, i, start, length,):
            quality = _encode_segment_and_compare(wd_dir, input_file, i, start, length, mid_crf)
            if quality:
                qualities.append(quality)

        _for_segments(fragments, get_quality)

        avg_quality = sum(qualities) / len(qualities) if qualities else 0
        logging.info(f"CRF: {mid_crf}, Average Quality (SSIM): {avg_quality}")

        return avg_quality

    crf_min, crf_max = 0, 51
    best_crf, best_quality = bisection_search(evaluate_crf, min_value = crf_min, max_value = crf_max, target_condition=lambda avg_quality: avg_quality >= requested_quality)

    if best_crf is not None and best_quality is not None:
        logging.info(f"Finished CRF bisection. Optimal CRF: {best_crf} with quality: {best_quality}")
    else:
        logging.warning(f"Finished CRF bisection. Could not find CRF matching desired quality ({requested_quality}).")
    return best_crf

def final_encode(input_file, crf, extra_params):
    """Perform the final encoding with the best CRF using the determined extra_params."""
    _, basename, ext = utils.split_path(input_file)

    logging.info(f"Starting final encoding with CRF: {crf} and extra params: {extra_params}")
    final_output_file = f"{basename}.temp.{ext}"
    encode_video(input_file, final_output_file, crf, "veryslow", extra_params)

    original_size = os.path.getsize(input_file)
    final_size = os.path.getsize(final_output_file)
    size_reduction = (final_size / original_size) * 100

    # Measure SSIM again after final encoding
    final_quality = calculate_quality(input_file, final_output_file)

    if final_size < original_size:
        subprocess.run(["exiftool", "-overwrite_original", "-TagsFromFile", input_file, "-all:all>all:all", final_output_file], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        os.rename(final_output_file, input_file)
        logging.info(
            f"Final CRF: {crf}, Final Encoding SSIM: {final_quality}, Encoded Size: {final_size} bytes, "
            f"Size reduced by: {original_size - final_size} bytes "
            f"({size_reduction:.2f}% of original size)"
        )
    else:
        os.remove(final_output_file)
        logging.warning(
            f"Final CRF: {crf}, Final Encoding SSIM: {final_quality}, "
            f"Encoded file is larger than the original. Keeping the original file."
        )

def main(directory):
    logging.info("Starting video processing")
    video_files = find_video_files(directory)

    for file in video_files:
        logging.info(f"Processing {file}")
        best_crf = find_optimal_crf(file)
        if best_crf is not None and False:
            # increase crf by one as veryslow preset will be used, so result should be above 0.98 quality anyway
            final_encode(file, best_crf + 1, [])
        logging.info(f"Finished processing {file}")

    logging.info("Video processing completed")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python encode_videos.py /path/to/directory")
        sys.exit(1)

    logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.INFO)
    directory = sys.argv[1]
    main(directory)
