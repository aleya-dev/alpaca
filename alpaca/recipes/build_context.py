import hashlib
import importlib.metadata
import json
from os import makedirs
from os.path import exists, join
from pathlib import Path
from shutil import rmtree
from typing import Self

from alpaca.common.logging import logger
from alpaca.common.shell_command import ShellCommand
from alpaca.configuration.configuration import Configuration

__version__ = importlib.metadata.version("aleya-alpaca")

from alpaca.recipes.version import Version

_build_context_json_name = "build_context.json"

from alpaca.recipes.recipe_description import RecipeDescription


class BuildContext:
    def __init__(self, recipe_path: Path | str, configuration: Configuration | None = None):

        self.configuration = configuration
        self.description = RecipeDescription()

        self.recipe_path = Path(recipe_path).expanduser().resolve()
        self.workspace_path: Path | None = None

        self._allow_workspace_cleanup = True

    def create_workspace_directories(self):
        self._allow_workspace_cleanup = False

        if exists(self.workspace_path):
            if self.configuration.package_delete_workspace:
                logger.verbose(f"Removing existing workspace {self.workspace_path}")
                rmtree(self.workspace_path)
            else:
                raise Exception(f"Workspace '{self.workspace_path}' must not exist. "
                                "If you wish to delete it, you can use the --delete-workdir option.")

        logger.debug("Creating workspace directories: %s", self.workspace_path)

        makedirs(self.workspace_path)
        makedirs(self.source_directory)
        makedirs(self.build_directory)
        makedirs(self.package_directory)

        self._allow_workspace_cleanup = True

    def delete_workspace_directories(self):
        """
        Clean up the workspace directories created for this recipe context.
        This will remove the source, build, and package directories.
        """

        if not self._allow_workspace_cleanup:
            return

        if not exists(self.workspace_path):
            return

        if not self.configuration.keep_build_directory:
            logger.info("Cleaning up build directories...")
            rmtree(self.workspace_path)
        else:
            logger.info("Keeping build directories...")

    @property
    def recipe_directory(self) -> Path:
        """
        Get the path where the recipe is located.
        """
        return Path(self.recipe_path).parent

    @property
    def source_directory(self) -> Path:
        """
        Get the path where the source files are located.
        """
        return Path(self.workspace_path, "source")

    @property
    def build_directory(self) -> Path:
        """
        Get the path where the build files are located.
        """
        return Path(self.workspace_path, "build")

    @property
    def package_directory(self) -> Path:
        """
        Get the path where the package files are located.
        """
        return Path(self.workspace_path, "package")

    def write_package_hash(self):
        """
        Compute a hash of the package script and options to determine if a prebuilt binary is available
        This can be used to skip building from source if the binary is already available

        Returns:
            str: The hash of the package script and options
        """

        with open(self.recipe_path, "r") as file:
            package_script = file.read()

        hash_object = hashlib.sha256()
        hash_object.update(package_script.encode("utf-8"))
        hash_object.update(self.configuration.target_architecture.encode("utf-8"))

        # Left for future use if options are needed
        # for key in sorted(self.options.keys()):
        #    hash_object.update(key.encode("utf-8"))
        #    hash_object.update(str(self.options[key]).encode("utf-8"))

        with open(join(self.package_directory, ".hash"), "w") as hash_file:
            hash_file.write(hash_object.hexdigest())

    def get_environment_variables(self) -> dict[str, str]:
        """
        Get the environment variables for the recipe.
        This can be used to pass additional variables to the package script.

        Returns:
            dict[str, str]: The environment variables for the recipe.
        """

        env = {
            "alpaca_build": "1",
            "alpaca_version": __version__,
            "target_architecture": self.configuration.target_architecture,
            "target_platform": "linux",
            "c_flags": self.configuration.c_flags,
            "cpp_flags": self.configuration.cpp_flags,
            "ld_flags": self.configuration.ld_flags,
            "make_flags": self.configuration.make_flags,
            "ninja_flags": self.configuration.ninja_flags
        }

        if self.workspace_path:
            env.update({
                "source_directory": str(self.source_directory),
                "build_directory": str(self.build_directory),
                "package_directory": str(self.package_directory)
            })

        if self.description.name is not None:
            env.update({"name": self.description.name})

        if self.description.version is not None:
            env.update({"version": str(self.description.version)})

        if self.description.release is not None:
            env.update({"release": self.description.release})

        return env

    def write_build_context_json(self):
        build_context = {
            "configuration": {
                "name": self.description.name,
                "version": str(self.description.version),
                "release": self.description.release,
                "url": self.description.url,
                "licenses": self.description.licenses,
                "dependencies": self.description.dependencies,
                "build_dependencies": self.description.build_dependencies,
                "sources": self.description.sources,
                "sha256sums": self.description.sha256sums,
                "available_options": self.description.available_options},
            "recipe_path": str(self.recipe_path),
            "workspace_path": str(self.workspace_path)}

        build_context_path = self.workspace_path / _build_context_json_name

        with open(build_context_path, "w") as f:
            json.dump(build_context, f, indent=4)

    @classmethod
    def create_from_recipe(cls, configuration: Configuration, recipe_path: Path | str) -> Self:
        recipe_path = Path(recipe_path).expanduser().resolve()

        if not exists(recipe_path):
            raise Exception(f"Recipe not found: '{recipe_path}'")

        logger.debug(f"Loading package description from {recipe_path}")

        build_context = BuildContext(recipe_path=recipe_path, configuration=configuration)

        build_context.description.name = build_context._read_recipe_variable("name")
        build_context.description.version = Version(build_context._read_recipe_variable("version"))
        build_context.description.release = build_context._read_recipe_variable("release")

        build_context.workspace_path = Path(
            join(configuration.package_workspace_path, build_context.description.name,
                 str(build_context.description.version)))

        build_context.description.url = build_context._read_recipe_variable("url")

        build_context.description.licenses = build_context._read_recipe_variable("licenses", is_array=True).split()

        build_context.description.dependencies = build_context._read_recipe_variable("dependencies",
                                                                                     is_array=True).split()

        build_context.description.build_dependencies = build_context._read_recipe_variable("build_dependencies",
                                                                                           is_array=True).split()

        build_context.description.sources = build_context._read_recipe_variable("sources", is_array=True).split()

        build_context.description.sha256sums = build_context._read_recipe_variable("sha256sums", is_array=True).split()

        build_context.description.available_options = build_context._read_recipe_variable("package_options",
                                                                                          is_array=True).split()

        return build_context

    @classmethod
    def create_from_workspace(cls, configuration: Configuration, workspace_path: Path | str) -> Self:
        build_context_path = Path(workspace_path) / _build_context_json_name

        if not exists(build_context_path):
            raise FileNotFoundError(f"Build context JSON file not found: {build_context_path}")

        with open(build_context_path, "r") as f:
            build_context_data = json.load(f)

        recipe_path = Path(build_context_data["recipe_path"])

        if not exists(recipe_path):
            raise FileNotFoundError(f"Recipe file not found: {recipe_path}")

        workspace_path = Path(build_context_data["workspace_path"])

        if not exists(workspace_path):
            raise FileNotFoundError(f"Workspace path does not exist: {workspace_path}")

        build_context = cls(recipe_path, configuration)
        build_context.workspace_path = workspace_path
        build_context.description.name = build_context_data["configuration"]["name"]
        build_context.description.version = build_context_data["configuration"]["version"]
        build_context.description.release = build_context_data["configuration"]["release"]
        build_context.description.url = build_context_data["configuration"]["url"]
        build_context.description.licenses = build_context_data["configuration"]["licenses"]
        build_context.description.dependencies = build_context_data["configuration"]["dependencies"]
        build_context.description.build_dependencies = build_context_data["configuration"]["build_dependencies"]
        build_context.description.sources = build_context_data["configuration"]["sources"]
        build_context.description.sha256sums = build_context_data["configuration"]["sha256sums"]
        build_context.description.available_options = build_context_data["configuration"]["available_options"]

        return build_context

    def _read_recipe_variable(self, variable: str, is_array: bool = False) -> str:
        """
        Read or parse a variable from the recipe.

        Args:
            variable: The name of the variable to read.
            is_array: If True, the variable is treated as an array.

        Returns:
            str: The value of the variable, or an error message if the variable is not defined.
        """

        var_ref = f"${{{variable}[@]}}" if is_array else f"${{{variable}}}"

        command = f'''
            source "{str(self.recipe_path)}"
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

        return ShellCommand.exec_get_value(configuration=self.configuration, command=command,
                                           environment=self.get_environment_variables())
