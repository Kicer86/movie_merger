
import argparse

def setup_parser(parser: argparse.ArgumentParser):
    parser.description = (
        "Concatenate is a tool for concatenating video files splitted into many files into one.\n"
        "For example if you have movie consisting of two files: movie-cd1.avi and movie-cd2.avi\n"
        "then 'concatenate' tool will glue them into one file 'movie.avi'.\n"
        "If your files come with subtitle files, you may want to use 'merge' tool first\n"
        "to merge video files with corresponding subtitle files.\n"
        "Otherwise you will end up with one video file and two subtitle files for cd1 and cd2 which will be useless now"
    )


def run(args):
    pass
