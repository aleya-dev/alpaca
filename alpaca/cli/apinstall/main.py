import importlib.metadata
from argparse import ArgumentParser
from logging import DEBUG, INFO
from pathlib import Path

from alpaca.core.common.logging import setup_logging, VERBOSE, get_logger
from alpaca.core.package import Package

__version__ = importlib.metadata.version("aleya-alpaca")

from alpaca.core.package_registry import PackageRegistry


def _create_arg_parser() -> ArgumentParser:
    parser = ArgumentParser(
        description=f"Alpaca Install - The Aleya Package Configuration Assistant ({__version__})")

    parser.add_argument("--verbose", "-v", action="store_true", default=None, help="Enable verbose output")

    parser.add_argument("--extra-verbose", "-vv", action="store_true", default=None, help="Enable extra verbose output")

    parser.add_argument("--version", action="version", version=f"Alpaca version: {__version__}")

    parser.add_argument("--yes", "-y", action="store_true", default=None,
                        help="Assume yes to all questions during installation")

    parser.add_argument("--prefix", "-p", type=str, default="/", help="Installation prefix (default: /)")

    parser.add_argument("--developer", action="store_true", default=None, help="Enable developer debug mode")

    parser.add_argument("package", type=str, help="Path to a package file to install")

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

        package_path = Path(args.package).resolve()

        logger.debug(f"Loading package from {package_path}")
        with Package(package_path) as package:
            print(package.recipe_info)

            registry = PackageRegistry(prefix=args.prefix)
            registry.install(package, ask_confirmation=not args.yes)
    except Exception as e:
        if args.developer:
            raise

        logger.critical("An error occurred: %s", e, exc_info=False)
        exit(1)


if __name__ == "__main__":
    main()
