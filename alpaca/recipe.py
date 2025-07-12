from os.path import join, exists
from pathlib import Path
from typing import Self, List

from alpaca.common.logging import logger
from alpaca.common.shell_command import ShellCommand
from alpaca.common.version import Version
from alpaca.configuration import Configuration
from alpaca.package_dependency import PackageDependencyType, PackageDependency
from alpaca.package_info import PackageInfo
from alpaca.repository_cache import RepositoryCache, RepositorySearchType


class Recipe:
    """
    Represents a package recipe, including its metadata.

    Attributes:
        configuration (Configuration): The configuration for the build process.
        info (PackageInfo): The package information containing metadata about the package.
        path (Path | None): The path to the recipe file, if available. If loaded from a package info file,
            the recipe path will be None. Even if we were to store it, it might be a completely different system.

        sources (list[str]): A list of source URLs for the package.
        sha256sums (list[str]): A list of SHA256 checksums for the sources.
    """

    def __init__(self, configuration: Configuration, package_info: PackageInfo, recipe_path: str | Path,
        sources: list[str], sha256sums: list[str]):
        """
        Initialize the Recipe with the given configuration and package information. For internal use only.

        Args:
            configuration (Configuration): The configuration for the build process.
            package_info (PackageInfo): The package information containing metadata about the package.
            recipe_path (str | Path | None): The path to the recipe file, if available. Defaults to None.
        """
        self.configuration = configuration
        self.info = package_info
        self.path: Path = Path(recipe_path).expanduser().resolve()

        self.sources: list[str] = sources
        self.sha256sums: list[str] = sha256sums

        if len(self.sources) != len(self.sha256sums):
            raise ValueError(
                f"Number of sources ({len(self.sources)}) does not match number of sha256sums ({len(self.sha256sums)})")



    @property
    def recipe_directory(self) -> Path:
        """
        Get the path where the recipe is located, if available.
        """
        return Path(self.path).parent

    @classmethod
    def _read_recipe_variable(cls, configuration: Configuration, recipe_path: str | Path, variable: str,
                              environment: dict[str, str], is_array: bool = False) -> str | List[str]:
        """
        Read or parse a variable from the recipe.

        Args:
            configuration (Configuration): The configuration for the build process.
            recipe_path (str | Path): The path to the recipe file.
            variable (str): The name of the variable to read.
            environment (dict[str, str]): The environment variables to use during the command execution.
            is_array (bool): Whether the variable is an array. Defaults to False.

        Returns:
            str: The value of the variable, or an error message if the variable is not defined.
        """

        var_ref = f"${{{variable}[@]}}" if is_array else f"${{{variable}}}"

        command = f'''
            set -e
            source "{str(recipe_path)}"
            if declare -f {variable} >/dev/null && declare -p {variable} >/dev/null; then
                echo "Error: both a variable and a function named '{variable}' are defined" >&2
                exit 1
            elif declare -f {variable} >/dev/null; then
                {variable}
            elif declare -p {variable} >/dev/null; then
                printf '%s\\n' {var_ref}
            else
                echo "Error: neither a variable nor a function named '{variable}' is defined" >&2
                exit 1
            fi
        '''

        result = ShellCommand.exec_get_value(configuration=configuration, command=command, environment=environment)
        return result if not is_array else result.split()

    @classmethod
    def _resolve_dependencies_from_string(cls, configuration: Configuration, dependency_type: PackageDependencyType,
                              dependencies: List[str]) -> list[Self]:
        repository_cache = RepositoryCache(configuration)

        resolved_dependencies: list[PackageDependency] = []

        for dependency in dependencies:
            package_info_path = repository_cache.find_by_path(dependency, RepositorySearchType.PACKAGE_INFO)

            if not package_info_path:
                raise ValueError(f"Package info for '{dependency}' not found in the repository cache.")

            package_info = PackageInfo.read_json(package_info_path)

            resolved_dependencies.append(PackageDependency(
                package_type=dependency_type, atom=package_info.atom, dependencies=package_info.dependencies))

        return resolved_dependencies


    @classmethod
    def create_from_recipe_file(cls, configuration: Configuration, recipe_path: str | Path) -> Self:
        """
        Create a Recipe instance from a recipe file.

        Args:
            configuration: The Alpaca configuration.
            recipe_path: The path to the recipe file.

        Returns:
            Recipe: An instance of the Recipe class containing the package information.

        """
        if not exists(recipe_path):
            raise FileNotFoundError(f"Recipe file '{recipe_path}' does not exist.")

        environment = configuration.get_environment_variables()

        name = Recipe._read_recipe_variable(
            configuration=configuration, recipe_path=recipe_path, environment=environment, variable="name")
        stream = Recipe._read_recipe_variable(
            configuration=configuration, recipe_path=recipe_path, environment=environment, variable="stream")
        version = Version(Recipe._read_recipe_variable(
            configuration=configuration, recipe_path=recipe_path, environment=environment, variable="version"))
        release = Recipe._read_recipe_variable(
            configuration=configuration, recipe_path=recipe_path, environment=environment, variable="release")

        environment.update({
            "ALPACA_RECIPE_NAME": name,
            "ALPACA_RECIPE_VERSION": str(version),
            "ALPACA_RECIPE_RELEASE": release
        })

        url = Recipe._read_recipe_variable(
            configuration=configuration, recipe_path=recipe_path, environment=environment, variable="url")
        licenses = Recipe._read_recipe_variable(
            configuration=configuration, recipe_path=recipe_path, environment=environment, variable="licenses",
            is_array=True)
        dependencies = Recipe._resolve_dependencies_from_string(configuration, PackageDependencyType.RUNTIME,
                                                    Recipe._read_recipe_variable(
                                                        configuration=configuration, recipe_path=recipe_path,
                                                        environment=environment, variable="dependencies",
                                                        is_array=True))
        build_dependencies = Recipe._resolve_dependencies_from_string(configuration, PackageDependencyType.BUILD,
                                                          Recipe._read_recipe_variable(
                                                              configuration=configuration, recipe_path=recipe_path,
                                                              environment=environment,
                                                              variable="build_dependencies", is_array=True))
        sources = Recipe._read_recipe_variable(
            configuration=configuration, recipe_path=recipe_path, environment=environment, variable="sources",
            is_array=True)
        sha256sums = Recipe._read_recipe_variable(
            configuration=configuration, recipe_path=recipe_path, environment=environment, variable="sha256sums",
            is_array=True)

        package_info = PackageInfo(
            path=recipe_path,
            name=name,
            stream=stream,
            version=version,
            release=release,
            url=url,
            licenses=licenses,
            dependencies=dependencies,
            build_dependencies=build_dependencies,
        )

        return cls(configuration, package_info, recipe_path, sources, sha256sums)

    @classmethod
    def read_from_package_info(cls, configuration: Configuration, package_info: PackageInfo) -> Self:
        """
        Create a Recipe instance from a RecipeInfo object.

        Args:
            configuration: The Alpaca configuration.
            package_info: The RecipeInfo object containing processed information about a recipe.

        Returns:
            Recipe: An instance of the Recipe class containing the package information.
        """
        # The recipe path is a file called .recipe next to the given package info file
        recipe_path = join(package_info.package_info_directory, ".recipe")

        logger.debug(f"Using recipe from {recipe_path}")
        return cls(configuration, package_info, recipe_path, [], [])
