from os import rename, chmod, remove
from os.path import join, exists, lexists
from pathlib import Path
from shutil import rmtree

from alpaca.common.confirmation import ask_user_confirmation
from alpaca.common.file_downloader import download_file
from alpaca.common.hash import check_file_hash_from_file
from alpaca.common.logging import logger
from alpaca.configuration import Configuration
from alpaca.package_dependency import PackageDependency
from alpaca.package_file import PackageFile
from alpaca.package_file_info import get_total_bytes
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

                    download_file(url, Path(self.configuration.download_cache_path),
                                  show_progress=self.configuration.show_download_progress)
                    download_file(f"{url}.sha256", Path(self.configuration.download_cache_path),
                                  show_progress=self.configuration.show_download_progress)
                except Exception as e:
                    continue

                logger.info(f"Installing package {package_info.name} from web repository: {repository.path}")

                download_path = join(self.configuration.download_cache_path,
                                     f"{package_info.file_atom}{self.configuration.package_file_extension}")
                check_file_hash_from_file(download_path)

                with PackageFile(download_path) as package_file:
                    self.install_package(package_file, ask_confirmation=ask_confirmation)

                logger.verbose(f"Removing downloaded package file: {download_path}")
                remove(download_path)

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

        package_file_tempdir = Path(join(self.configuration.download_cache_path, package_info.file_atom))
        package_file.extract(package_file_tempdir)

        database_path = Path(join(self.configuration.package_install_database_path, package_info.name))

        if not database_path.exists():
            logger.verbose(f"Creating database directory: {database_path}")
            database_path.mkdir(parents=True, exist_ok=True)

        for meta_file in [".recipe", ".file_info", ".package_info"]:
            src = package_file_tempdir / meta_file
            dst = database_path / meta_file
            logger.verbose(f"Moving metadata: {src} -> {dst}")
            rename(src, dst)

        for source_file in package_file_tempdir.rglob("*"):
            if source_file.is_dir():
                continue

            relative_path = source_file.relative_to(package_file_tempdir)
            destination_file = Path(self.configuration.prefix) / relative_path
            destination_parent = destination_file.parent

            if not destination_parent.exists():
                logger.verbose(f"Creating directory: {destination_parent}")
                destination_parent.mkdir(parents=True, exist_ok=True)

            if source_file.is_symlink():
                symlink_target = source_file.readlink()

                overwrite = False
                if lexists(destination_file):
                    overwrite = True
                    destination_file.unlink()

                logger.verbose(f"{destination_file} -> {symlink_target} ({"overwriting" if overwrite else "creating symlink"})")
                destination_file.symlink_to(symlink_target)
            else:
                mode = source_file.stat().st_mode

                overwrite = False
                if destination_file.exists():
                    overwrite = True
                    remove(destination_file)

                logger.verbose(f"{"overwriting" if overwrite else "copying"} {relative_path} -> {destination_file}")
                rename(source_file, destination_file)
                chmod(destination_file, mode & 0o777)

        logger.verbose(f"Removing temporary directory: {package_file_tempdir}")
        rmtree(package_file_tempdir, ignore_errors=True)

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