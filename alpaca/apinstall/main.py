from argparse import ArgumentParser, Namespace
from os.path import exists

from alpaca.common.alpaca_application import handle_main
from alpaca.common.host_info import is_aleya_linux_host
from alpaca.common.logging import logger
from alpaca.configuration.configuration import Configuration
from alpaca.packages.package_context import PackageContext
from alpaca.packages.package_file_info import get_total_bytes


def _bytes_to_human(num):
    for unit in ("", "Ki", "Mi", "Gi"):

        if abs(num) < 1024.0:
            return f"{num:3.1f}{unit}B"

        num /= 1024.0

    return f"{num:.1f}TiB"


def _create_arg_parser(parser: ArgumentParser) -> ArgumentParser:
    # .alpaca-package.tgz is a configuration string; Parsed arguments are part of the configuration...
    parser.add_argument("package", type=str, help="The path to a binary package (.alpaca-package.tgz).")
    parser.add_argument("--target", "-t", type=str,
                        help="The target directory where the package will be installed. "
                             "Defaults to '/' if not specified.")

    return parser


def _install_main(args: Namespace, config: Configuration):
    package_path = args.package

    if not package_path.endswith(config.package_file_extension):
        raise ValueError(
            f"Invalid package file: {package_path}. Expected a file with extension '{config.package_file_extension}'.")

    if not exists(package_path):
        raise FileNotFoundError(f"Package file '{package_path}' does not exist.")

    if config.prefix == '/' and not is_aleya_linux_host():
        raise ValueError("Target directory '/' is not allowed on non-Aleya Linux hosts. "
                         "If you intended to install a new system, please specify a the mounted "
                         "target directory using --target.")

    with PackageContext(package_path) as package_context:
        description = package_context.description

        logger.info(f"Installing package '{description.name}' version '{description.version}' "
                    f"from '{package_path}' to target directory '{args.target}'.")

        logger.info(f"Total install size: {_bytes_to_human(get_total_bytes(package_context.file_info))}")

        logger.debug(f"Package hash: {package_context.hash}")

def main():
    handle_main(
        "install",
        require_root=True,
        disallow_root=False,
        create_arguments_callback=_create_arg_parser,
        main_function_callback=_install_main)


if __name__ == "__main__":
    main()
