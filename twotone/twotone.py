
import argparse
import logging
import sys

from tools import merge

TOOLS = {
    "merge": (merge.setup_parser, merge.run, "Batch tool: merge video file with subtitles into one MKV file"),
}


def main(argv):
    parser = argparse.ArgumentParser(
        description="Videos manipulation toolkit",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
    subparsers = parser.add_subparsers(dest="tool", help="Available tools:")

    for tool_name, (setup_parser, _, desc) in TOOLS.items():
        tool_parser = subparsers.add_parser(
            tool_name,
            help=desc,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter
        )
        setup_parser(tool_parser)

    args = parser.parse_args()

    if args.tool is None:
        parser.print_help()
        sys.exit(1)

    if args.tool in TOOLS:
        TOOLS[args.tool][1](args)
    else:
        print(f"Error: Unknown tool {args.tool}")
        sys.exit(1)


if __name__ == '__main__':
    logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.INFO)
    try:
        main(sys.argv[1:])
    except RuntimeError as e:
        logging.error(f"Unexpected error occurred: {e}. Terminating")
        exit(1)
