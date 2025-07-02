import importlib.metadata
from argparse import ArgumentParser

from alpaca.common.logging import enable_verbose_logging, logger
from alpaca.common.repository_cache import RepositoryCache
from alpaca.configuration.configuration import Configuration

__version__ = importlib.metadata.version("aleya-alpaca")

from alpaca.recipes.recipe_context import RecipeContext


def _create_arg_parser():
    parser = ArgumentParser(description=f"AlpaCA build - The Aleya Package Configuration Assistant ({__version__})")

    parser.add_argument("package", type=str, help="Name of the package to install (e.g. binutils or binutils-2.44-1 "
                                                  "or a recipe file like ./binutils-2.44-1.recipe)")

    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose output")

    parser.add_argument("--quiet", "-q", action="store_true", help="Limit build and copy output to errors only")

    parser.add_argument("--version", action="version", version=f"AlpaCA version: {__version__}")

    parser.add_argument("--keep", "-k", action="store_true", help="Keep the build directory if the build fails")

    parser.add_argument("--no-check", action="store_true", help="Skip the package check phase")

    parser.add_argument("--workdir", "-w", type=str,
                        help="A working directory for the recipe to be built in. The directory must not exist")

    parser.add_argument("--delete-workdir", "-d", action="store_true",
                        help="Delete the working directory automatically if it exists")

    parser.add_argument("--download", action="store_true",
                        help="Force redownloading all files regardless of download cache.")

    parser.add_argument("--output", "-o", type=str, help="The directory where to place the built package.")

    return parser


def _is_root_user() -> bool:
    """
    Check if the current user is the root user.

    Returns:
        bool: True if the current user is root, False otherwise.
    """
    import os
    return os.getuid() == 0


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

        config.ensure_executables_exist()

        logger.debug("-=-=-=-=-=-=-=-=-=-=-=-=-=")
        logger.debug(config.dump_config())
        logger.debug("-=-=-=-=-=-=-=-=-=-=-=-=-=")

        repo_cache = RepositoryCache(config)

        if _is_root_user():
            raise Exception("Running 'apbuild' as root is not allowed. Please run as a normal user.")

        logger.debug("This software is provided under GNU GPL v3.0")
        logger.debug("This software comes with ABSOLUTELY NO WARRANTY")
        logger.debug("This software is free software, and you are welcome to redistribute it under certain conditions")
        logger.debug("For more information, visit https://www.gnu.org/licenses/gpl-3.0.html")

        recipe_path = repo_cache.find_recipe(args.package)

        if recipe_path is None:
            logger.fatal(f"Could not find recipe for package '{args.package}'.")
            exit(1)

        logger.info(f"Installing package: {recipe_path}")
        logger.debug(f"Full path: {recipe_path}")

        context = RecipeContext(config, recipe_path)
        context.create_package()

    except Exception as e:
        logger.fatal(f"An error has occurred: {e}")
        exit(1)

if __name__ == "__main__":
    main()
