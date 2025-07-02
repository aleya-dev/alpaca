from argparse import ArgumentParser, Namespace

from alpaca.common.alpaca_application import handle_main
from alpaca.common.tar import compress_tar
from alpaca.configuration.configuration import Configuration
from alpaca.packages.package_file_info import write_file_info


def _create_arg_parser(parser: ArgumentParser) -> ArgumentParser:
    subparsers = parser.add_subparsers(dest="command", required=True)

    fileinfo_parser = subparsers.add_parser("fileinfo",
                                            help="Generate a .fileinfo file for a given package or recipe file.")

    fileinfo_parser.add_argument("package_dir", type=str,
                                 help="The package directory of the current build context.")

    compress_package_parser = subparsers.add_parser("compress",
                                                    help="Compress a package directory into a .alpaca-package.tgz file.")
    compress_package_parser.add_argument("package_dir", type=str,
                                         help="The package directory to compress.")
    compress_package_parser.add_argument("output_archive", type=str,
                                         help="The output archive file path (e.g., /path/to/archive.tgz).")

    return parser


def _command_main(args: Namespace, configuration: Configuration):
    if args.command == "fileinfo":
        write_file_info(args.package_dir)
    elif args.command == "compress":
        compress_tar(args.package_dir, args.output_archive)


def main():
    handle_main(
        "command",
        require_root=False,
        disallow_root=False,
        create_arguments_callback=_create_arg_parser,
        main_function_callback=_command_main)


if __name__ == "__main__":
    main()
