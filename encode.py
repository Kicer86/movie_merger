
import os
import logging
import subprocess
import sys


# Determine the log file name based on the script name
script_name = os.path.splitext(os.path.basename(__file__))[0]
log_filename = f"{script_name}.log"

# Set up logging
logging.basicConfig(filename=log_filename, level=logging.INFO, format="%(asctime)s %(message)s")

def find_video_files(directory):
    """Find video files with specified extensions."""
    video_files = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.lower().endswith(('.mov', '.mp4', '.mkv')):
                video_files.append(os.path.join(root, file))
    return video_files

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

def find_optimal_crf(input_file, basename, ext):
    """Find the optimal CRF using bisection."""
    original_size = os.path.getsize(input_file)
    crf_min, crf_max = 5, 45
    best_crf = crf_min
    best_quality = None
    best_size = original_size

    logging.info(f"Starting CRF bisection for {input_file} with veryfast preset")

    while crf_min <= crf_max:
        mid_crf = (crf_min + crf_max) // 2
        output_file = f"{basename}.temp.{ext}"
        encode_video(input_file, output_file, mid_crf, preset="veryfast")

        encoded_size = os.path.getsize(output_file)
        quality = calculate_quality(input_file, output_file)
        logging.info(f"CRF: {mid_crf}, Quality (SSIM): {quality}, Encoded Size: {encoded_size} bytes")

        if quality and quality >= 0.98:
            best_crf = mid_crf
            best_quality = quality
            best_size = encoded_size
            crf_min = mid_crf + 1
        else:
            crf_max = mid_crf - 1

        os.remove(output_file)

    logging.info(f"Finished CRF bisection. Optimal CRF: {best_crf}, Encoded size: {best_size} bytes")

    # Return the best CRF and whether the best size is smaller than the original
    if best_size < original_size:
        return best_crf
    else:
        logging.warning(
            f"Optimal CRF: {best_crf}, but encoded size {best_size} bytes is not smaller than original size "
            f"{original_size} bytes. Skipping final encoding and keeping the original file."
        )
        return None

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
        best_crf = find_optimal_crf(file, basename, ext)
        if best_crf is not None:
            # increase crf by one as veryslow preset will be used, so result should be above 0.98 quality anyway
            final_encode(file, basename, ext, best_crf + 1, [])
        logging.info(f"Finished processing {file}")

    logging.info("Video processing completed")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 encode_videos.py /path/to/directory")
        sys.exit(1)

    directory = sys.argv[1]
    main(directory)

