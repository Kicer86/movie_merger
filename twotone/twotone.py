
import argparse
import logging
import sys

from .tools import merge, subtitles_fixer, encode

TOOLS = {
    "merge": (merge.setup_parser, merge.run, "Batch tool: merge video file with subtitles into one MKV file"),
    "subtitles_fix": (subtitles_fixer.setup_parser, subtitles_fixer.run, "Batch tool: fixes some specific issues with subtitles. Do not use until you are sure it will help for your problems."),
    "encode": (encode.setup_parser, encode.run, "Batch tool: transcode videos preserving quality."),
}


def execute(argv):
    parser = argparse.ArgumentParser(
        description='Videos manipulation toolkit. '
                    'By default all tools do nothing but showing what would be done. '
                    'Use --no-dry-run option to perform actual operation. '
                    'Please mind that ALL source files will be modified, so consider making a backup. '
                    'It is safe to stop any tool with ctrl+c - it will quit '
                    'gracefully in a while.',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    parser.add_argument("--verbose",
                        action="store_true",
                        help="Enable verbose output")
    parser.add_argument("--no-dry-run", "-r",
                        action='store_true',
                        default=False,
                        help='Perform actual operation.')
    subparsers = parser.add_subparsers(dest="tool", help="Available tools:")

    for tool_name, (setup_parser, _, desc) in TOOLS.items():
        tool_parser = subparsers.add_parser(
            tool_name,
            help=desc,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter
        )
        setup_parser(tool_parser)

    args = parser.parse_args(args = argv)

    if args.tool is None:
        parser.print_help()
        sys.exit(1)

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    if args.tool in TOOLS:
        TOOLS[args.tool][1](args)
    else:
        print(f"Error: Unknown tool {args.tool}")
        sys.exit(1)

def main():
    logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.INFO)
    try:
        execute(sys.argv[1:])
    except RuntimeError as e:
        logging.error(f"Unexpected error occurred: {e}. Terminating")
        exit(1)

if __name__ == '__main__':
    main()
