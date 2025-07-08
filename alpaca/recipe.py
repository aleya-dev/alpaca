from os.path import join, exists
from pathlib import Path
from typing import Self, List

from alpaca.common.logging import logger
from alpaca.common.shell_command import ShellCommand
from alpaca.common.version import Version
from alpaca.configuration import Configuration
from alpaca.recipe_info import RecipeInfo


class Recipe:
    """
    Represents a package recipe, including its metadata.

    Attributes:
        configuration (Configuration): The configuration for the build process.
        info (RecipeInfo): The recipe information containing metadata about the package.
        path (Path | None): The path to the recipe file, if available. If loaded from a recipe info file,
            the recipe path will be None. Even if we were to store it, it might be a completely different system.
    """

    def __init__(self, configuration: Configuration, recipe_info: RecipeInfo, recipe_path: str | Path):
        """
        Initialize the Recipe with the given configuration and recipe information. For internal use only.

        Args:
            configuration (Configuration): The configuration for the build process.
            recipe_info (RecipeInfo): The recipe information containing metadata about the package.
            recipe_path (str | Path | None): The path to the recipe file, if available. Defaults to None.
        """
        self.configuration = configuration
        self.info = recipe_info
        self.path: Path = Path(recipe_path).expanduser().resolve()

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
    def create_from_recipe_file(cls, configuration: Configuration, recipe_path: str | Path) -> Self:
        """
        Create a Recipe instance from a recipe file.

        Args:
            configuration: The Alpaca configuration.
            recipe_path: The path to the recipe file.

        Returns:
            Recipe: An instance of the Recipe class containing the recipe information.

        """
        if not exists(recipe_path):
            raise FileNotFoundError(f"Recipe file '{recipe_path}' does not exist.")

        environment = configuration.get_environment_variables()

        name = Recipe._read_recipe_variable(
            configuration=configuration, recipe_path=recipe_path, environment=environment, variable="name")
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
        dependencies = Recipe._read_recipe_variable(
            configuration=configuration, recipe_path=recipe_path, environment=environment, variable="dependencies",
            is_array=True)
        build_dependencies = Recipe._read_recipe_variable(
            configuration=configuration, recipe_path=recipe_path, environment=environment,
            variable="build_dependencies", is_array=True)
        sources = Recipe._read_recipe_variable(
            configuration=configuration, recipe_path=recipe_path, environment=environment, variable="sources",
            is_array=True)
        sha256sums = Recipe._read_recipe_variable(
            configuration=configuration, recipe_path=recipe_path, environment=environment, variable="sha256sums",
            is_array=True)

        recipe_info = RecipeInfo(
            path=recipe_path,
            name=name,
            version=version,
            release=release,
            url=url,
            licenses=licenses,
            dependencies=dependencies,
            build_dependencies=build_dependencies,
            sources=sources,
            sha256sums=sha256sums
        )

        return cls(configuration, recipe_info, recipe_path)

    @classmethod
    def read_from_recipe_info(cls, configuration: Configuration, recipe_info: RecipeInfo) -> Self:
        """
        Create a Recipe instance from a RecipeInfo object.

        Args:
            configuration: The Alpaca configuration.
            recipe_info: The RecipeInfo object containing processed information about a recipe.

        Returns:
            Recipe: An instance of the Recipe class containing the recipe information.
        """
        # The recipe path is a file called .recipe next to the given recipe info file
        recipe_path = join(recipe_info.recipe_info_directory, ".recipe")

        logger.debug(f"Using recipe from {recipe_path}")
        return cls(configuration, recipe_info, recipe_path)
