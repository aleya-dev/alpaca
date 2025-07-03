from argparse import ArgumentParser, Namespace
from os.path import join

from alpaca.common.alpaca_application import handle_main
from alpaca.common.logging import logger
from alpaca.common.tar import compress_tar
from alpaca.configuration.configuration import Configuration
from alpaca.packages.package_file_info import write_file_info
from alpaca.recipes.build_context import BuildContext


def _create_arg_parser(parser: ArgumentParser) -> ArgumentParser:
    subparsers = parser.add_subparsers(dest="command", required=True)

    compress_package_parser = subparsers.add_parser("deploy",
                                                   help="Handle all package deploy steps. "
                                                   "This is intended to be used by alpaca itself to handle the "
                                                   "deploy steps of a package inside of a fakeroot.")
    compress_package_parser.add_argument("workspace_dir", type=str,
                                         help="The path to the workspace root of the package to deploy during package.")

    compress_package_parser.add_argument("output_dir", type=str,
                                         help="The output directory where the package will be deployed.")

    return parser


def _command_main(args: Namespace, configuration: Configuration):
    if args.command == "deploy":
        logger.info(f"Deploying package from workspace: {args.workspace_dir}")

        build_context = BuildContext.create_from_workspace(configuration, args.workspace_dir)
        write_file_info(build_context.package_directory)
        build_context.description.write_package_description(
            build_context.package_directory / ".package_info"
        )
        build_context.write_package_hash()

        output_archive = join(args.output_dir,
                                f"{build_context.description.name}-{build_context.description.version}-"
                                f"{build_context.description.release}{configuration.package_file_extension}")

        compress_tar(build_context.package_directory, output_archive)


def main():
    handle_main(
        "command",
        require_root=False,
        disallow_root=False,
        create_arguments_callback=_create_arg_parser,
        main_function_callback=_command_main)


if __name__ == "__main__":
    main()
