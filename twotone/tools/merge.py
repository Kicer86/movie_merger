
import argparse

def setup_parser(parser: argparse.ArgumentParser):
    parser.add_argument("--input", type=str, required=True, help="Input file path")
    parser.add_argument("--output", type=str, required=True, help="Output file path")
    parser.add_argument("--format", type=str, choices=["png", "jpg"], help="Output format")

def run(args):
    print(args)
