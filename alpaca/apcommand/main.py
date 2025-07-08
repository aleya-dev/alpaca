from argparse import ArgumentParser, Namespace
from os.path import join, exists

from alpaca.build_context import BuildContext
from alpaca.common.alpaca_application import handle_main
from alpaca.common.logging import logger
from alpaca.configuration.configuration import Configuration
from alpaca.recipe import Recipe
from alpaca.recipe_info import RecipeInfo


def _create_arg_parser(parser: ArgumentParser) -> ArgumentParser:
    subparsers = parser.add_subparsers(dest="command", required=True)

    compress_package_parser = subparsers.add_parser("deploy",
                                                   help="Handle all package deploy steps. "
                                                   "This is intended to be used by alpaca itself to handle the "
                                                   "deploy steps of a package inside of a fakeroot.")
    compress_package_parser.add_argument("workspace_dir", type=str,
                                         help="The path to the workspace root of the package to deploy during package.")

    compress_package_parser.add_argument("output", type=str,
                                         help="The output directory where the package will be deployed.")

    return parser


def _command_main(args: Namespace, configuration: Configuration):
    if args.command == "deploy":
        recipe_info = RecipeInfo.read_json(join(args.workspace_dir, ".recipe_info"))
        recipe = Recipe.read_from_recipe_info(configuration, recipe_info)

        context = BuildContext(recipe)
        context.deploy_package()

def main():
    handle_main(
        "command",
        require_root=False,
        disallow_root=False,
        create_arguments_callback=_create_arg_parser,
        main_function_callback=_command_main)


if __name__ == "__main__":
    main()
