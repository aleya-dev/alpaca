from alpaca.logging import logger, enable_debug_logging, enable_verbose_logging
from alpaca.package_manager import PackageManager
from alpaca.configuration import Configuration

import argparse
import os
import shutil

import importlib.metadata

__version__ = importlib.metadata.version("alpaca")


def _create_arg_parser():
    parser = argparse.ArgumentParser(
        description=f"AlpaCA - The Aleya Package Configuration Assistant ({__version__})"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose output"
    )
    parser.add_argument(
        "--debug", "-d", action="store_true", help="Enable debug output"
    )
    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Limit build and copy output to errors only",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"AlpaCA version: {__version__}",
    )

    subparsers = parser.add_subparsers(dest="command", help="Subcommand help")
    subparsers.add_parser("update", help="Update package lists")

    install_parser = subparsers.add_parser("install", help="Install a package")
    install_parser.add_argument(
        "package",
        type=str,
        help="Name of the package to install (e.g. binutils or binutils-2.44-1)",
    )
    install_parser.add_argument(
        "--build",
        "-b",
        action="store_true",
        help="Build the package from source, even if a prebuilt binary is available",
    )

    install_parser.add_argument(
        "--keep",
        "-k",
        action="store_true",
        help="Keep the build directory if the build fails",
    )

    remove_parser = subparsers.add_parser("remove", help="Remove a package")
    remove_parser.add_argument(
        "package",
        type=str,
        help="Name of the package to remove (e.g. binutils or binutils-2.44-1)",
    )

    prune_parser = subparsers.add_parser(
        "prune",
        help="Cleanup all build intermediates. "
        "This does not remove installed packages or anything from the binary cache",
    )
    prune_parser.add_argument(
        "--all", "-a", action="store_true", help="Also clean up the local binary cache"
    )

    return parser


def _create_workspace_directories():
    config = Configuration()

    logger.verbose(f"Ensuring workspace directories at {config.data_directory} exist")
    os.makedirs(config.data_directory, exist_ok=True)

    # The repositories directory is used to store the local cache of repositories
    os.makedirs(config.get_repository_base_path(), exist_ok=True)

    # The workspace directory is used to store sources and build intermediate files
    os.makedirs(config.get_workspace_base_path(), exist_ok=True)

    # The local bincache is used to store prebuilt binaries that are built from source
    # on the local machine. In the future scripting will be added to allow for the
    # distribution of these binaries to other machines.
    os.makedirs(config.get_package_local_binary_cache_base_path(), exist_ok=True)


def _handle_update():
    config = Configuration()

    logger.verbose("Ensuring repo cache path exists")
    os.makedirs(config.data_directory, exist_ok=True)

    logger.info("Updating package lists...")

    for repo in config.repositories:
        repo.update()

    logger.info("Package lists updated")


def _handle_install(package_atom: str):
    package_manager = PackageManager()
    package = package_manager.find_package(package_atom)
    package.build()


def _handle_prune(prune_all: bool):
    config = Configuration()

    if not config.user_is_root:
        raise PermissionError("You must be root to prune build intermediates")

    logger.info("Pruning build intermediates...")

    shutil.rmtree(config.get_workspace_base_path())

    if prune_all:
        logger.info("Pruning local binary cache...")
        shutil.rmtree(config.get_package_local_binary_cache_base_path())

    logger.info("Pruning complete")


def main():
    try:
        parser = _create_arg_parser()
        args = parser.parse_args()

        # This code is a little wonky, we can't use "config." yet until we've parsed the command line arguments fully,
        # and configured the log levels; otherwise half the log messages will be suppressed because the logger isn't
        # configured yet.
        if args.debug:
            enable_debug_logging()

        if args.verbose:
            enable_verbose_logging()

        config = Configuration()

        if args.verbose or config.verbose:
            enable_verbose_logging()
            config.verbose = True
            logger.verbose("Verbose output enabled")

        if args.debug or config.debug:
            enable_debug_logging()
            config.debug = True
            logger.debug("Debug output enabled")

        if args.quiet:
            config.suppress_build_output = True

        logger.debug("This software is provided under GNU GPL v3.0")
        logger.debug("This software comes with ABSOLUTELY NO WARRANTY")
        logger.debug(
            "This software is free software, and you are welcome to redistribute it under certain conditions"
        )
        logger.debug(
            "For more information, visit https://www.gnu.org/licenses/gpl-3.0.html"
        )

        if not config.is_aleya_linux_host:
            logger.warning(
                "Not running on an Aleya Linux host. Physically installing packages will be skipped."
            )

        if not config.user_is_root:
            raise PermissionError("You must be root to update package lists")

        _create_workspace_directories()

        if args.command == "update":
            _handle_update()
        elif args.command == "install":
            if args.build:
                config.force_build_from_source = True

            if args.keep:
                config.keep_intermediates_on_failure = True

            _handle_install(args.package)
        elif args.command == "remove":
            pass
        elif args.command == "prune":
            _handle_prune(args.all)
        else:
            parser.print_help()
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        logger.verbose("Stack trace:", exc_info=True)
        exit(1)


if __name__ == "__main__":
    main()
