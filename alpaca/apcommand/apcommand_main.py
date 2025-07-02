import importlib.metadata
from argparse import ArgumentParser

__version__ = importlib.metadata.version("aleya-alpaca")


from alpaca.common.logging import enable_verbose_logging, logger
from alpaca.configuration.configuration import Configuration
from alpaca.recipes.package_file_info import write_file_info


def _create_arg_parser():
    parser = ArgumentParser(
        description=f"AlpaCA command - The Aleya Package Configuration Assistant ({__version__})")
    subparsers = parser.add_subparsers(dest="command", required=True)

    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose output")

    fileinfo_parser = subparsers.add_parser("fileinfo",
                                            help="Generate a .fileinfo file for a given package or recipe file.")

    fileinfo_parser.add_argument("package_dir", type=str,
                                 help="The package directory of the current build context.")

    return parser

def main():
    try:
        parser = _create_arg_parser()
        args = parser.parse_args()

        # Hack to ensure that verbose logs from the configuration module are printed
        if args.verbose:
            enable_verbose_logging()

        config = Configuration.create_application_config(args)

        if config.verbose_output:
            enable_verbose_logging()

        logger.debug("-=-=-=-=-=-=-=-=-=-=-=-=-=")
        logger.debug(config.dump_config())
        logger.debug("-=-=-=-=-=-=-=-=-=-=-=-=-=")

        if args.command == "fileinfo":
            write_file_info(args.package_dir)

    except Exception as e:
        print(f"An error occurred: {e}")
        exit(1)


if __name__ == "__main__":
    main()
