from os import makedirs
from os.path import join, exists

from alpaca.common.confirmation import ask_user_confirmation
from alpaca.common.logging import logger
from alpaca.configuration import Configuration
from alpaca.package_file import PackageFile
from alpaca.package_file_info import get_total_bytes
from alpaca.recipe import Recipe
from alpaca.recipe_info import RecipeInfo


def _bytes_to_human(num):
    for unit in ("", "Ki", "Mi", "Gi"):

        if abs(num) < 1024.0:
            return f"{num:3.1f}{unit}B"

        num /= 1024.0

    return f"{num:.1f}TiB"


class SystemContext:
    def __init__(self, configuration: Configuration):
        self.configuration = configuration

    def install_package(self, package_file: PackageFile, ask_confirmation: bool = True):
        recipe_info = package_file.read_recipe_info()

        state = self.get_install_state(recipe_info.name)
        updating = True if state else False

        if state and state.version == recipe_info.version:
            logger.info(f"- Overwriting {recipe_info.name} ({recipe_info.version})")
        elif updating:
            logger.info(f"- Updating {recipe_info.name} ({state.version} => {recipe_info.version})")
        else:
            logger.info(f"- Installing {recipe_info.name} ({recipe_info.version})")
        logger.verbose(f"Source: {package_file.package_path}")
        logger.verbose(f"Prefix: {self.configuration.prefix}")

        file_info = package_file.read_file_info()
        logger.info(f"Total install size: {_bytes_to_human(get_total_bytes(file_info))}")
        logger.info("")

        if ask_confirmation and not ask_user_confirmation("Install package?", default=False):
            logger.info("Installation cancelled by user.")
            return

        database_path = join(self.configuration.package_install_database_path, recipe_info.name)

        if not updating and not exists(database_path):
            logger.verbose(f"Creating database directory: {database_path}")
            makedirs(database_path)

        # TODO: Special case for when updating. We should remove files that no longer exist in the package.

        package_file.extract_file(".recipe", database_path)
        package_file.extract_file(".file_info", database_path)
        package_file.extract_file(".recipe_info", database_path)
        package_file.extract(self.configuration.prefix)

        logger.info(f"Package {recipe_info.name} ({recipe_info.version}) installed successfully.")

    def get_install_state(self, package_name: str) -> RecipeInfo | None:
        logger.verbose(f"Checking install state for package: {package_name}")
        database_path = join(self.configuration.package_install_database_path, package_name)
        recipe_info_path = join(database_path, ".recipe_info")

        if not exists(recipe_info_path):
            return None

        return RecipeInfo.read_json(recipe_info_path)

    def are_all_installed(self, dependencies: list[Recipe]) -> bool:
        for dependency in dependencies:
            installed = self.get_install_state(dependency.info.name)

            if not installed:
                logger.error(f"Required dependency {dependency.info.name}/{dependency.info.version}-{dependency.info.release} is not installed.")
                return False

            if installed.version != dependency.info.version or installed.release != dependency.info.release:
                logger.error(f"Dependency {dependency.info.name} is installed with version {installed.version}-{installed.release}, "
                             f"but recipe requires version {dependency.info.version}-{dependency.info.release}.")
                return False

        return True