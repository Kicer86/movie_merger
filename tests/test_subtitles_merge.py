
import os.path
import subprocess
import unittest

import utils
import twotone
from common import TestDataWorkingDirectory, list_files, add_test_media, hashes


class SubtitlesMerge(unittest.TestCase):

    def test_dry_run_is_respected(self):
        with TestDataWorkingDirectory() as td:
            add_test_media(".*mp4|.*mov|.*srt", td.path)

            hashes_before = hashes(td.path)
            self.assertEqual(len(hashes_before), 2 * 9)        # 9 videos and 9 subtitles expected
            twotone.run([td.path, "--dry-run"])
            hashes_after = hashes(td.path)

            self.assertEqual(hashes_before, hashes_after)

    def test_dry_run_with_conversion_is_respected(self):
        with TestDataWorkingDirectory() as td:
            add_test_media("herd-of-horses-in-fog.*(mp4|txt)", td.path)

            hashes_before = hashes(td.path)
            self.assertEqual(len(hashes_before), 2)
            twotone.run([td.path, "--dry-run"])
            hashes_after = hashes(td.path)

            self.assertEqual(hashes_before, hashes_after)

    def test_many_videos_conversion(self):
        with TestDataWorkingDirectory() as td:
            add_test_media(".*mp4|.*mov|.*srt", td.path)

            files_before = list_files(td.path)
            self.assertEqual(len(files_before), 2 * 9)        # 9 videos and 9 subtitles expected

            twotone.run([td.path])

            files_after = list_files(td.path)
            self.assertEqual(len(files_after), 1 * 9)        # 9 mkv videos expected

            for video in files_after:
                self.assertEqual(video[-4:], ".mkv")
                tracks = utils.get_video_data(video)
                self.assertEqual(len(tracks.video_tracks), 1)
                self.assertEqual(len(tracks.subtitles), 1)

    def test_appending_subtitles_to_mkv_with_subtitles(self):
        with TestDataWorkingDirectory() as td:

            # combine mp4 with srt into mkv
            add_test_media("Atoms.*(mp4|srt)", td.path)

            twotone.run([td.path])

            # combine mkv with srt into mkv with 2 subtitles
            add_test_media("Atoms.*srt", td.path)

            twotone.run([td.path])

            # verify results
            files_after = list_files(td.path)
            self.assertEqual(len(files_after), 1)

            video = files_after[0]
            self.assertEqual(video[-4:], ".mkv")
            tracks = utils.get_video_data(video)
            self.assertEqual(len(tracks.video_tracks), 1)
            self.assertEqual(len(tracks.subtitles), 2)

    def test_subtitles_language(self):
        with TestDataWorkingDirectory() as td:

            # combine mp4 with srt into mkv
            add_test_media("Atoms.*(mp4|srt)", td.path)

            twotone.run([td.path, "-l", "pol"])

            # verify results
            files_after = list_files(td.path)
            self.assertEqual(len(files_after), 1)

            video = files_after[0]
            self.assertEqual(video[-4:], ".mkv")
            tracks = utils.get_video_data(video)
            self.assertEqual(len(tracks.video_tracks), 1)
            self.assertEqual(len(tracks.subtitles), 1)
            self.assertEqual(tracks.subtitles[0].language, "pol")

    def test_multiple_subtitles_for_single_file(self):
        with TestDataWorkingDirectory() as td:

            # one file in directory with many subtitles
            add_test_media("Atoms.*mp4", td.path)
            add_test_media("Atoms.*srt", td.path, ["PL", "EN", "DE"])

            twotone.run([td.path])

            # verify results: all subtitle-like files should be sucked in
            files_after = list_files(td.path)
            self.assertEqual(len(files_after), 1)

            video = files_after[0]
            self.assertEqual(video[-4:], ".mkv")
            tracks = utils.get_video_data(video)
            self.assertEqual(len(tracks.video_tracks), 1)
            self.assertEqual(len(tracks.subtitles), 3)

    def test_raw_txt_subtitles_conversion(self):
        # Allow automatic txt to srt conversion
        with TestDataWorkingDirectory() as td:
            add_test_media("herd-of-horses-in-fog.*(mp4|txt)", td.path)

            twotone.run([td.path])

            # verify results
            files_after = list_files(td.path)
            self.assertEqual(len(files_after), 1)

            video = files_after[0]
            self.assertEqual(video[-4:], ".mkv")
            tracks = utils.get_video_data(video)
            self.assertEqual(len(tracks.video_tracks), 1)
            self.assertEqual(len(tracks.subtitles), 1)

    def test_invalid_subtitle_extension(self):
        with TestDataWorkingDirectory() as td:
            add_test_media("Frog.*mp4", td.path)

            with open(os.path.join(td.path, "Frog_en.srt"), "w") as sf:
                sf.write("00:00:00:Hello World\n")
                sf.write("00:00:06:This is some sample subtitle in english\n")

            with open(os.path.join(td.path, "Frog_pl.srt"), "w", encoding="cp1250") as sf:
                sf.write("00:00:00:Witaj Świecie\n")
                sf.write("00:00:06:To jest przykładowy tekst po polsku\n")

            twotone.run([td.path])

            files_after = list_files(td.path)
            self.assertEqual(len(files_after), 1)

            video = files_after[0]
            self.assertEqual(video[-4:], ".mkv")
            tracks = utils.get_video_data(video)
            self.assertEqual(len(tracks.video_tracks), 1)
            self.assertEqual(len(tracks.subtitles), 2)

    def test_multilevel_structure(self):
        with TestDataWorkingDirectory() as td:
            add_test_media("sea-waves-crashing-on-beach-shore.*mp4", td.path)
            add_test_media("sea-waves-crashing-on-beach-shore.*srt", td.path, ["PL", "EN"])

            subdir = os.path.join(td.path, "subdir")
            os.mkdir(subdir)

            add_test_media("Grass.*mp4", subdir)
            add_test_media("Grass.*srt", subdir, ["PL", "EN"])

            twotone.run([td.path])

            files_after = list_files(td.path)
            self.assertEqual(len(files_after), 2)

            for video in files_after:
                self.assertEqual(video[-4:], ".mkv")
                tracks = utils.get_video_data(video)
                self.assertEqual(len(tracks.video_tracks), 1)
                self.assertEqual(len(tracks.subtitles), 2)

    def test_subtitles_in_subdirectory(self):
        with TestDataWorkingDirectory() as td:
            add_test_media("sea-waves-crashing-on-beach-shore.*mp4", td.path)
            add_test_media("sea-waves-crashing-on-beach-shore.*srt", td.path, ["PL", "EN"])

            subdir = os.path.join(td.path, "subdir")
            os.mkdir(subdir)

            add_test_media("sea-waves-crashing-on-beach-shore.*srt", subdir, ["DE", "CS"])

            twotone.run([td.path])

            files_after = list_files(td.path)
            self.assertEqual(len(files_after), 1)

            video = files_after[0]
            self.assertEqual(video[-4:], ".mkv")
            tracks = utils.get_video_data(video)
            self.assertEqual(len(tracks.video_tracks), 1)
            self.assertEqual(len(tracks.subtitles), 4)

    def test_appending_subtitles_to_mkv_with_subtitles(self):
        with TestDataWorkingDirectory() as td:

            # combine mp4 with srt into mkv
            add_test_media("fog-over-mountainside.*(mp4|srt)", td.path)

            twotone.run([td.path, "-l", "de"])

            # combine mkv with srt into mkv with 2 subtitles
            add_test_media("fog-over-mountainside.*srt", td.path)

            twotone.run([td.path, "-l", "pl"])

            # verify results
            files_after = list_files(td.path)
            self.assertEqual(len(files_after), 1)

            video = files_after[0]
            self.assertEqual(video[-4:], ".mkv")
            tracks = utils.get_video_data(video)
            self.assertEqual(len(tracks.video_tracks), 1)
            self.assertEqual(len(tracks.subtitles), 2)
            self.assertEqual(tracks.subtitles[0].language, "ger")
            self.assertEqual(tracks.subtitles[1].language, "pol")

    def test_video_override(self):
        with TestDataWorkingDirectory() as td:

            # create mkv file
            add_test_media("Woman.*(mp4|srt)", td.path)
            twotone.run([td.path])

            # now there are two movies with the same name but different extension.
            # twotone should not overwrite mkv movie
            add_test_media("Woman.*(mp4|srt)", td.path)
            twotone.run([td.path])

            # verify results
            files_after = list_files(td.path)
            self.assertEqual(len(files_after), 2)

if __name__ == '__main__':
    unittest.main()
