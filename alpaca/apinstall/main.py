from argparse import ArgumentParser, Namespace
from os.path import exists

from alpaca.common.alpaca_application import handle_main
from alpaca.common.host_info import is_aleya_linux_host
from alpaca.configuration import Configuration
from alpaca.package_file import PackageFile
from alpaca.system_context import SystemContext


def _create_arg_parser(parser: ArgumentParser) -> ArgumentParser:
    # .alpaca-package.tgz is a configuration string; Parsed arguments are part of the configuration...
    parser.add_argument("package", type=str, help="The path to a binary package (.alpaca-package.tgz).")

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

    system = SystemContext(config)

    with PackageFile(package_path) as package_file:
        system.install_package(package_file)

def main():
    handle_main(
        "install",
        require_root=True,
        disallow_root=False,
        create_arguments_callback=_create_arg_parser,
        main_function_callback=_install_main)


if __name__ == "__main__":
    main()
