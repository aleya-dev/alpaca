from os import makedirs
from os.path import join, exists
from pathlib import Path

from alpaca.atom import decompose_package_atom_from_name
from alpaca.common.confirmation import ask_user_confirmation
from alpaca.common.file_downloader import download_file
from alpaca.common.hash import check_file_hash_from_file
from alpaca.common.logging import logger
from alpaca.configuration import Configuration
from alpaca.package_dependency import PackageDependency
from alpaca.package_file import PackageFile
from alpaca.package_file_info import get_total_bytes
from alpaca.recipe import Recipe
from alpaca.package_info import PackageInfo
from alpaca.repository_cache import RepositoryCache, RepositorySearchType
from alpaca.repository_ref import RepositoryType


def _bytes_to_human(num):
    for unit in ("", "Ki", "Mi", "Gi"):

        if abs(num) < 1024.0:
            return f"{num:3.1f}{unit}B"

        num /= 1024.0

    return f"{num:.1f}TiB"


class SystemContext:
    def __init__(self, configuration: Configuration):
        self.configuration = configuration

    def install_package_by_package_dependency(self, package_dependency: PackageDependency, ask_confirmation: bool = True):
        cache = RepositoryCache(self.configuration)
        package_info_path = cache.find_by_path(package_dependency.atom, search_type=RepositorySearchType.PACKAGE_INFO)

        if not package_info_path:
            logger.error(f"Recipe {package_dependency.atom} not found in repository cache.")
            return

        package_info = PackageInfo.read_json(package_info_path)

        for repository in self.configuration.repositories:
            if repository.type == RepositoryType.LOCAL:
                package_file = join(repository.path, package_info.stream, package_info.name,
                                f"{package_info.file_atom}{self.configuration.package_file_extension}")

                if not exists(package_file):
                    continue

                logger.info(f"Installing package {package_info.name} from local repository: {repository.path}")

                check_file_hash_from_file(package_file)

                with PackageFile(package_file) as package_file:
                    self.install_package(package_file, ask_confirmation=ask_confirmation)

                return
            elif repository.type == RepositoryType.WEB:
                try:
                    url = f"{repository.path}/{package_info.stream}/{package_info.name}/{package_info.file_atom}{self.configuration.package_file_extension}"

                    download_file(self.configuration, url, Path(self.configuration.download_cache_path),
                                  show_progress=self.configuration.show_download_progress)
                    download_file(self.configuration, f"{url}.sha256", Path(self.configuration.download_cache_path),
                                  show_progress=self.configuration.show_download_progress)
                except Exception as e:
                    continue

                logger.info(f"Installing package {package_info.name} from web repository: {repository.path}")

                download_path = join(self.configuration.download_cache_path,
                                     f"{package_info.file_atom}{self.configuration.package_file_extension}")
                check_file_hash_from_file(download_path)

                with PackageFile(download_path) as package_file:
                    self.install_package(package_file, ask_confirmation=ask_confirmation)

                # TODO: Delete the downloaded package file after installation
                return

            elif repository.type == RepositoryType.GIT:
                logger.verbose(f"Skipping repository {repository.path} of type {repository.type} for package installation.")
                continue

        raise ValueError(f"Package {package_info.name} not found in any package server. It must be built from source.")

    def install_package(self, package_file: PackageFile, ask_confirmation: bool = True):
        package_info = package_file.read_package_info()

        state = self.get_install_state_by_name(package_info.name)
        updating = True if state else False

        if state and state.version == package_info.version:
            logger.info(f"- Overwriting {package_info.name} ({package_info.version})")
        elif updating:
            logger.info(f"- Updating {package_info.name} ({state.version} => {package_info.version})")
        else:
            logger.info(f"- Installing {package_info.name} ({package_info.version})")

        file_info = package_file.read_file_info()
        logger.info(f"Total install size: {_bytes_to_human(get_total_bytes(file_info))}")
        logger.info("")

        if ask_confirmation and not ask_user_confirmation("Install package?", default=False):
            logger.info("Installation cancelled by user.")
            return

        database_path = join(self.configuration.package_install_database_path, package_info.name)

        if not updating and not exists(database_path):
            logger.verbose(f"Creating database directory: {database_path}")
            makedirs(database_path)

        # TODO: Special case for when updating. We should remove files that no longer exist in the package.

        package_file.extract_file(".recipe", database_path)
        package_file.extract_file(".file_info", database_path)
        package_file.extract_file(".package_info", database_path)
        package_file.extract(self.configuration.prefix)

        logger.info(f"Package {package_info.name} ({package_info.version}) installed successfully.")

    def install_from_package_dependencies(self, dependencies: list[PackageDependency], ask_confirmation: bool = True):
        """
        Install a list of recipes to the system

        Args:
            dependencies (list[PackageDependency]): A list of package dependencies to install.
            ask_confirmation (bool): Whether to ask for user confirmation before installing each package.
        """

        if ask_confirmation and not ask_user_confirmation("Install packages?", default=False):
            logger.info("Installation cancelled by user.")
            return

        for dependency in dependencies:
            logger.info(f"Installing recipe: {dependency.name}/{dependency.version})")
            self.install_package_by_package_dependency(dependency, ask_confirmation=False)

    def get_install_state_by_name(self, name: str) -> PackageInfo | None:
        logger.verbose(f"Checking install state for package: {name}")
        database_path = join(self.configuration.package_install_database_path, name)
        package_info_path = join(database_path, ".package_info")

        if not exists(package_info_path):
            return None

        return PackageInfo.read_json(package_info_path)

    def are_all_installed(self, dependencies: list[PackageDependency]) -> bool:
        for dependency in dependencies:
            installed = self.get_install_state_by_name(dependency.name)

            if not installed:
                logger.error(f"Required dependency {dependency.name}/{dependency.version} is not installed.")
                return False

            if dependency.version != f"{installed.version}-{installed.release}":
                logger.error(
                    f"Dependency {dependency.name} is installed with version {installed.version}-{installed.release}, "
                    f"but recipe requires version {dependency.version}.")
                return False

        return True