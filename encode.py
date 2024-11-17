
import os
import logging
import random
import subprocess
import sys
import tempfile

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

def select_random_fragments(video_file, duration, num_fragments=5, fragment_length=5):
    """Select random fragments from the video for analysis."""
    fragments = []
    for _ in range(num_fragments):
        start_time = random.uniform(0, max(0, duration - fragment_length))
        fragments.append((start_time, fragment_length))
    return fragments

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

def find_optimal_crf(input_file, ext):
    """Find the optimal CRF using bisection."""
    original_size = os.path.getsize(input_file)
    crf_min, crf_max = 5, 45
    best_crf = crf_min
    best_quality = None
    best_size = original_size
    filename = utils.split_path(input_file)[1]

    duration = get_video_duration(input_file)
    if not duration:
        return None

    num_fragments = max(3, min(10, int(duration // 30)))
    fragments = select_random_fragments(input_file, duration, num_fragments)

    logging.info(f"Starting CRF bisection for {input_file} with veryfast preset using {num_fragments} fragments")

    while crf_min <= crf_max:
        mid_crf = (crf_min + crf_max) // 2
        qualities = []

        with tempfile.TemporaryDirectory() as wd_dir:
            for i, (start, length) in enumerate(fragments):
                fragment_output = os.path.join(wd_dir, f"{filename}_frag{i}.{ext}")
                encoded_fragment_output = os.path.join(wd_dir, f"{filename}_frag{i}.enc.{ext}")

                extract_fragment(input_file, start, length, fragment_output)
                encode_video(fragment_output, encoded_fragment_output, mid_crf, "veryfast")

                quality = calculate_quality(fragment_output, encoded_fragment_output)
                if quality:
                    qualities.append(quality)

        avg_quality = sum(qualities) / len(qualities) if qualities else 0
        logging.info(f"CRF: {mid_crf}, Average Quality (SSIM): {avg_quality}")

        if avg_quality >= 0.98:
            best_crf = mid_crf
            best_quality = avg_quality
            crf_min = mid_crf + 1
        else:
            crf_max = mid_crf - 1

    logging.info(f"Finished CRF bisection. Optimal CRF: {best_crf}")
    return best_crf

def final_encode(input_file, basename, ext, crf, extra_params):
    """Perform the final encoding with the best CRF using the determined extra_params."""
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
        basename, ext = os.path.splitext(file)
        ext = ext[1:]  # Remove the dot from the extension
        best_crf = find_optimal_crf(file, ext)
        if best_crf is not None and False:
            # increase crf by one as veryslow preset will be used, so result should be above 0.98 quality anyway
            final_encode(file, basename, ext, best_crf + 1, [])
        logging.info(f"Finished processing {file}")

    logging.info("Video processing completed")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python encode_videos.py /path/to/directory")
        sys.exit(1)

    logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.INFO)
    directory = sys.argv[1]
    main(directory)
