
import os
import unittest

import twotone
from common import TestDataWorkingDirectory, file_tracks, list_files, add_test_media
from utils import get_video_data

class SimpleSubtitlesMerge(unittest.TestCase):

    def test_english_recognition(self):
        with TestDataWorkingDirectory() as td:
            add_test_media("Frog.*mp4", td.path)

            with open(os.path.join(td.path, "Frog.txt"), "w") as sf:
                sf.write("00:00:00:Hello World\n")
                sf.write("00:00:06:This is some sample subtitle in english\n")

            twotone.run([td.path, "-l", "auto"])

            files_after = list_files(td.path)
            self.assertEqual(len(files_after), 1)

            video = files_after[0]
            self.assertEqual(video[-4:], ".mkv")
            tracks = file_tracks(video)
            self.assertEqual(len(tracks["video"]), 1)
            self.assertEqual(len(tracks["subtitle"]), 1)
            self.assertEqual(tracks["subtitle"][0]["tags"]["language"], "en")

    def test_polish_recognition(self):
        with TestDataWorkingDirectory() as td:
            add_test_media("Frog.*mp4", td.path)

            with open(os.path.join(td.path, "Frog.txt"), "w") as sf:
                sf.write("00:00:00:Witaj Świecie\n")
                sf.write("00:00:06:To jest przykładowy tekst po polsku\n")

            twotone.run([td.path, "-l", "auto"])

            files_after = list_files(td.path)
            self.assertEqual(len(files_after), 1)

            video = files_after[0]
            self.assertEqual(video[-4:], ".mkv")
            tracks = file_tracks(video)
            self.assertEqual(len(tracks["video"]), 1)
            self.assertEqual(len(tracks["subtitle"]), 1)
            self.assertEqual(tracks["subtitle"][0]["tags"]["language"], "pl")

    def test_language_priority(self):
        with TestDataWorkingDirectory() as td:
            add_test_media("close-up-of-flowers.*mp4", td.path)
            with open(os.path.join(td.path, "close-up-of-flowers_en.srt"), "w") as sf:
                sf.write("00:00:00:Hello World\n")
                sf.write("00:00:06:This is some sample subtitle in english\n")

            with open(os.path.join(td.path, "close-up-of-flowers_pl.srt"), "w") as sf:
                sf.write("00:00:00:Witaj Świecie\n")
                sf.write("00:00:06:To jest przykładowy tekst po polsku\n")

            with open(os.path.join(td.path, "close-up-of-flowers_de.srt"), "w") as sf:
                sf.write("00:00:00:Hallo Welt\n")
                sf.write("00:00:06:Dies ist ein Beispiel für einen Untertitel auf Deutsch\n")

            with open(os.path.join(td.path, "close-up-of-flowers_cz.srt"), "w") as sf:
                sf.write("00:00:00:Ahoj světe\n")
                sf.write("00:00:06:Toto je ukázka titulků v češtině\n")

            with open(os.path.join(td.path, "close-up-of-flowers_fr.srt"), "w") as sf:
                sf.write("00:00:00:Bonjour le monde\n")
                sf.write("00:00:06:Ceci est un exemple de sous-titre en français\n")

            twotone.run([td.path, "-l", "auto", "-p" "de,cs"])

            files_after = list_files(td.path)
            self.assertEqual(len(files_after), 1)

            video = files_after[0]
            tracks = get_video_data(video)
            self.assertEqual(len(tracks.subtitles), 5)
            self.assertEqual(tracks.subtitles[0].language, "de")
            self.assertEqual(tracks.subtitles[1].language, "cs")
            self.assertEqual(tracks.subtitles[0].default, 1)
            self.assertEqual(tracks.subtitles[1].default, 0)


if __name__ == '__main__':
    unittest.main()
