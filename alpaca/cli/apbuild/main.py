import importlib.metadata
from argparse import ArgumentParser
from logging import DEBUG, INFO
from pathlib import Path

from alpaca.core.common.logging import setup_logging, VERBOSE, get_logger
from alpaca.core.package_builder import PackageBuilder
from alpaca.core.recipe_info import RecipeInfo

__version__ = importlib.metadata.version("aleya-alpaca")


def _create_arg_parser() -> ArgumentParser:
    parser = ArgumentParser(
        description=f"Alpaca Build - The Aleya Package Configuration Assistant ({__version__})")

    parser.add_argument("--verbose", "-v", action="store_true", default=None, help="Enable verbose output")

    parser.add_argument("--extra-verbose", "-vv", action="store_true", default=None, help="Enable extra verbose output")

    parser.add_argument("--version", action="version", version=f"Alpaca version: {__version__}")

    parser.add_argument("--quiet", "-q", action="store_true", default=None, help="Suppress build output")

    parser.add_argument("--i-did-not-ask", "-f", action="store_true", default=None,
                        help="Repackage the package even if it already exists")

    parser.add_argument("--skip-hash-check", action="store_true", default=None,
                        help="Skip SHA256 hash verification for downloaded sources. " \
                             "WARNING: This is highly insecure and should only be used for testing purposes.")

    parser.add_argument("--skip-checks", action="store_true", default=None, help="Skip post-build checks")

    parser.add_argument("--developer", action="store_true", default=None, help="Enable developer debug mode")

    parser.add_argument("recipe", type=str, help="Path to a recipe file to build")

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

        if args.skip_hash_check:
            logger.warning("Skipping hash verification for sources. "
                           "This is highly insecure and should only be used for testing purposes.")

        recipe_path = Path(args.recipe).resolve()

        logger.debug(f"Loading recipe from {recipe_path}")
        recipe = RecipeInfo.parse_from_recipe(recipe_path)

        builder = PackageBuilder(recipe)

        builder.ensure_directories(delete_if_exists=args.i_did_not_ask)
        builder.handle_sources(skip_hash_check=args.skip_hash_check)
        builder.build(quiet=args.quiet)

        if not args.skip_checks:
            builder.check(quiet=args.quiet)

        for package in recipe.provides:
            logger.debug(f"({recipe.provides.index(package) + 1}/{len(recipe.provides)}) Building package: {package}")
            builder.call_package(package, verbose=args.verbose, extra_verbose=args.extra_verbose,
                                 developer_mode=args.developer, delete_if_exists=args.i_did_not_ask)

    except Exception as e:
        if args.developer:
            raise

        logger.critical("An error occurred: %s", e, exc_info=False)
        exit(1)


if __name__ == "__main__":
    main()
