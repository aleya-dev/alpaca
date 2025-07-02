from argparse import ArgumentParser, Namespace

from alpaca.common.alpaca_application import handle_main
from alpaca.common.logging import logger
from alpaca.common.repository_cache import RepositoryCache
from alpaca.configuration.configuration import Configuration
from alpaca.recipes.recipe_context import RecipeContext


def _create_arg_parser(parser: ArgumentParser) -> ArgumentParser:
    parser.add_argument("package", type=str, help="Name of the package to install (e.g. binutils or binutils-2.44-1 "
                                                  "or a recipe file like ./binutils-2.44-1.recipe)")

    parser.add_argument("--quiet", "-q", action="store_true", help="Limit build and copy output to errors only")

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


def _build_main(args: Namespace, config: Configuration):
    repo_cache = RepositoryCache(config)

    recipe_path = repo_cache.find_recipe(args.package)

    if recipe_path is None:
        raise FileNotFoundError(f"Could not find recipe for package '{args.package}'.")

    logger.info(f"Installing package: {recipe_path}")
    logger.debug(f"Full path: {recipe_path}")

    context = RecipeContext(config, recipe_path)
    context.create_package()


def main():
    handle_main(
        "build",
        require_root=False,
        disallow_root=True,
        create_arguments_callback=_create_arg_parser,
        main_function_callback=_build_main)


if __name__ == "__main__":
    main()
