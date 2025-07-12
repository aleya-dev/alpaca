from argparse import ArgumentParser, Namespace
from os.path import exists

from alpaca.common.alpaca_application import handle_main
from alpaca.common.host_info import is_aleya_linux_host
from alpaca.configuration import Configuration
from alpaca.package_file import PackageFile
from alpaca.package_info import PackageInfo
from alpaca.repository_cache import RepositoryCache, RepositorySearchType
from alpaca.system_context import SystemContext


def _create_arg_parser(parser: ArgumentParser) -> ArgumentParser:
    # TODO: .alpaca-package.tgz is a configuration string; Parsed arguments are part of the configuration...
    parser.add_argument("package", type=str, help="The path to a binary package (.alpaca-package.tgz).")

    parser.add_argument("--install-deps", "-i", action="store_true",
        help="Install all dependencies of the package before installing it.")

    parser.add_argument("--yes", "-y", action="store_true",
        help="Assume yes to all questions during the installation process.")

    return parser


def _install_main(args: Namespace, config: Configuration):
    package_ref = args.package

    if config.prefix == '/' and not is_aleya_linux_host():
        raise ValueError("Target directory '/' is not allowed on non-Aleya Linux hosts. "
                         "If you intended to install a new system, please specify a the mounted "
                         "target directory using --target.")

    system = SystemContext(config)

    if exists(package_ref):
        with PackageFile(package_ref) as package_file:
            system.install_package(package_file)
    else:
        repo_cache = RepositoryCache(config)
        package_path = repo_cache.find_by_path(package_ref, RepositorySearchType.PACKAGE_INFO)

        if not package_path:
            raise FileNotFoundError(f"Package '{package_ref}' not found in repository cache.")

        package_info = PackageInfo.read_json(package_path)

        if not system.are_all_installed(package_info.dependencies):
            if args.install_deps:
                system.install_from_package_dependencies(
                    package_info.package_dependency.get_installation_order(include_self=False),
                    ask_confirmation=not args.yes
                )
            else:
                raise RuntimeError(
                    "Cannot install package because not all dependencies are installed. "
                    "Please install the required dependencies first. Use --install-deps to install them automatically."
                )

        system.install_package_by_package_dependency(package_info.package_dependency, ask_confirmation=not args.yes)

def main():
    handle_main(
        "install",
        require_root=True,
        disallow_root=False,
        create_arguments_callback=_create_arg_parser,
        main_function_callback=_install_main)


if __name__ == "__main__":
    main()
