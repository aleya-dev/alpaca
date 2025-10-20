import importlib.metadata
from argparse import ArgumentParser
from logging import INFO, DEBUG
from pathlib import Path

from alpaca.core.common.configuration import Configuration
from alpaca.core.common.logging import setup_logging, VERBOSE, get_logger
from alpaca.core.package_builder import PackageBuilder
from alpaca.core.recipe_info import RecipeInfo

__version__ = importlib.metadata.version("aleya-alpaca")


def _create_arg_parser() -> ArgumentParser:
    parser = ArgumentParser(
        description=f"Alpaca Pack - The Aleya Package Configuration Assistant ({__version__})")

    parser.add_argument("--verbose", "-v", action="store_true", default=None, help="Enable verbose output")

    parser.add_argument("--extra-verbose", "-vv", action="store_true", default=None, help="Enable extra verbose output")

    parser.add_argument("--version", action="version", version=f"Alpaca version: {__version__}")

    parser.add_argument("--i-did-not-ask", "-f", action="store_true", default=None,
                        help="Repackage the package even if it already exists")

    parser.add_argument("--developer", action="store_true", default=None, help="Enable developer debug mode")

    parser.add_argument("package_dir", type=str, help="Path to the packaging working directory")

    parser.add_argument("package", type=str, help="Name of the package to build")

    parser.description = "This tool is part of internal Alpaca plumbing and is not supposed to be called directly. " \
                         "Use at your own risk."

    return parser


def main():
    setup_logging(level=INFO)
    logger = get_logger(__name__)

    parser = _create_arg_parser()
    args = parser.parse_args()

    try:
        if args.extra_verbose:
            setup_logging(level=VERBOSE)
            logger.verbose("Extra verbose logging enabled")
        elif args.verbose:
            setup_logging(level=DEBUG)
            logger.verbose("Verbose logging enabled")

        config = Configuration.create_application_config(args)

        package_dir = Path(args.package_dir).resolve()

        logger.debug(f"Loading recipe from {package_dir}")
        recipe = RecipeInfo.read_from_package_dir(package_dir)
        logger.info(recipe)

        builder = PackageBuilder(recipe, config)
        builder.package(args.package, delete_if_exists=args.i_did_not_ask)

    except Exception as e:
        if args.developer:
            raise

        logger.critical("An error occurred: %s", e, exc_info=False)
        exit(1)


if __name__ == "__main__":
    main()
