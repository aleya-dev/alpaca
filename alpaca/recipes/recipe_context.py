import hashlib
import importlib.metadata
import shutil
from os import makedirs
from os.path import exists, join, isfile, basename
from pathlib import Path
from shutil import rmtree
from tarfile import is_tarfile
from urllib.parse import urlparse

from alpaca.common.alpaca_tools import get_alpaca_tool_command
from alpaca.common.file_downloader import download_file
from alpaca.common.hash import check_file_hash_from_string
from alpaca.common.logging import logger
from alpaca.common.shell_command import ShellCommand
from alpaca.common.tar import extract_tar
from alpaca.configuration.configuration import Configuration
from alpaca.recipes.recipe_description import RecipeDescription
from alpaca.recipes.version import Version

__version__ = importlib.metadata.version("aleya-alpaca")


class RecipeContext:
    def __init__(self, configuration: Configuration, path: Path | str):
        """
        Initialize the RecipeContext with the given configuration and recipe path.

        A recipe context is used to manage the environment and variables for a specific package recipe during the
        build and package process.

        Args:
            configuration (Configuration): The configuration for the build process.
            path (Path | str): The path to the recipe file.

        Raises:
            Exception: If the recipe file does not exist.
        """

        self.configuration = configuration
        self.recipe_path = Path(path).expanduser().resolve()

        if not exists(path):
            raise Exception(f"Recipe not found: '{path}'")

        logger.debug(f"Loading package description from {path}")

        early_env = self._get_environment_variables(None, None, None)
        name = self._read_package_variable(self.recipe_path, "name", env=early_env)
        version = self._read_package_variable(self.recipe_path, "version", env=early_env)
        release = self._read_package_variable(self.recipe_path, "release", env=early_env)

        env = self._get_environment_variables(name, version, release)

        url = self._read_package_variable(self.recipe_path, "url", env=env)

        licenses = self._read_package_variable(self.recipe_path, "licenses", is_array=True, env=env).split()

        dependencies = self._read_package_variable(self.recipe_path, "dependencies", is_array=True, env=env).split()

        build_dependencies = self._read_package_variable(self.recipe_path, "build_dependencies", is_array=True,
                                                         env=env).split()

        sources = self._read_package_variable(self.recipe_path, "sources", is_array=True, env=env).split()

        sha256sums = self._read_package_variable(self.recipe_path, "sha256sums", is_array=True, env=env).split()

        available_options = self._read_package_variable(self.recipe_path, "package_options", is_array=True,
                                                        env=env).split()

        self.description = RecipeDescription(name=name, version=Version(version), release=release, url=url,
                                             licenses=licenses, dependencies=dependencies,
                                             build_dependencies=build_dependencies, sources=sources,
                                             sha256sums=sha256sums,
                                             available_options=available_options)

    def create_package(self):
        """
        Create the package by handling sources, building, checking, and packaging.

        This function will create a workspace directory structure, download sources, build the package,
        check the package, and finally package it into a tar.gz archive.
        """

        try:
            self._create_workspace_directories()
            self._handle_sources()
            self._handle_build()
            self._handle_check()
            self._handle_package()
        except Exception as e:
            raise
        finally:
            self._delete_workspace_directories()

    def _create_workspace_directories(self):
        workspace_path = self.configuration.package_workspace_path

        if exists(workspace_path):
            if self.configuration.package_delete_workspace:
                logger.verbose(f"Removing existing workspace {workspace_path}")
                rmtree(workspace_path)
            else:
                raise Exception(f"Workspace '{workspace_path}' must not exist.")

        logger.debug("Creating workspace directories: %s", workspace_path)

        makedirs(workspace_path)
        makedirs(self.source_directory)
        makedirs(self.build_directory)
        makedirs(self.package_directory)

    def _handle_sources(self):
        logger.info("Handle sources...")

        if len(self.description.sources) != len(self.description.sha256sums):
            raise Exception(f"Number of sources ({len(self.description.sources)}) does not match "
                            f"number of sha256sums ({len(self.description.sha256sums)})")

        if len(self.description.sources) == 0:
            return

        for source, sha256sum in zip(self.description.sources, self.description.sha256sums):
            filename = self._download_source_file(source, sha256sum)

            if is_tarfile(filename):
                logger.info(f"Extracting file {basename(filename)}...")
                extract_tar(Path(filename), self.source_directory)

        self._call_script_function(
            function_name="handle_sources",
            working_dir=self.source_directory
        )

    def _handle_build(self):
        """
        Build the package from source, if applicable. This function will call the handle_build function in the package
        script, if it exists. If the function does not exist, this will do nothing.
        """

        logger.info("Building package...")
        self._call_script_function(
            function_name="handle_build",
            working_dir=self.build_directory,
            print_output=not self.configuration.suppress_build_output
        )

    def _handle_check(self):
        """
        Check the package after building; typically this runs tests to ensure the package is built correctly.
        Not all packages have tests. It is up to the package maintainer to implement this function or not in
        the recipe.

        This function will call the handle_check function in the package script, if it exists. If the function does not
        exist, this will do nothing.
        """

        if self.configuration.skip_package_check:
            logger.warning(
                "Skipping package check. This can lead to unexpected behavior as packages may not be built correctly.")
            return

        logger.info("Checking package...")
        self._call_script_function(
            function_name="handle_check",
            working_dir=self.build_directory,
            print_output=not self.configuration.suppress_build_output
        )

    def _handle_package(self):
        """
        This function will call the handle_package function in the package script, if it exists.
        After that it will package the built package into a tar.xz archive to serve as the binary cache.
        """

        output_archive = join(self.configuration.package_artifact_path,
                              f"{self.description.name}-{self.description.version}-"
                              f"{self.description.release}{self.configuration.package_file_extension}")

        logger.info("Packaging package...")
        self._call_script_function(
            function_name="handle_package",
            working_dir=self.build_directory,
            post_script=f'''
                {get_alpaca_tool_command("apcommand")} fileinfo {self.package_directory}

                echo {self._compute_binary_hash()} > {self.package_directory}/.hash 

                {self.configuration.cat_executable} > {self.package_directory}/.package_info <<EOF
# Generated by Aleya Linux Alpaca {__version__}
name="{self.description.name}"
version="{self.description.version}"
release="{self.description.release}"
url="{self.description.url}"
licenses=({" ".join(self.description.licenses)})
dependencies=({" ".join(self.description.dependencies)})
build_dependencies=({" ".join(self.description.build_dependencies)})
sources=({" ".join(self.description.sources)})
sha256sums=({" ".join(self.description.sha256sums)})
package_options=({" ".join(self.description.available_options)})
EOF

                {self.configuration.tar_executable} -czvf {output_archive} -C {self.package_directory} .
            ''',
            print_output=not self.configuration.suppress_build_output,
            use_fakeroot=True
        )

    def _delete_workspace_directories(self):
        """
        Clean up the workspace directories created for this recipe context.
        This will remove the source, build, and package directories.

        Args:
            always_delete (bool): If True, always delete the workspace directories regardless of configuration.
                                  Defaults to False.
        """

        if not exists(self.configuration.package_workspace_path):
            return

        if self.configuration.keep_build_directory:
            logger.info("Keeping build directories...")
            return
        else:
            logger.info("Cleaning up build directories...")

        rmtree(self.configuration.package_workspace_path)

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
        return Path(self.configuration.package_workspace_path, "source")

    @property
    def build_directory(self) -> Path:
        """
        Get the path where the build files are located.
        """
        return Path(self.configuration.package_workspace_path, "build")

    @property
    def package_directory(self) -> Path:
        """
        Get the path where the package files are located.
        """
        return Path(self.configuration.package_workspace_path, "package")

    def _compute_binary_hash(self) -> str:
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

        return hash_object.hexdigest()

    def _read_package_variable(self, path: Path, variable: str, env: dict[str, str] | None = None,
                               is_array: bool = False) -> str:
        var_ref = f"${{{variable}[@]}}" if is_array else f"${{{variable}}}"

        command = f'''
            source "{str(path)}"
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

        return ShellCommand.exec_get_value(configuration=self.configuration, command=command, environment=env)

    def _call_script_function(self, function_name: str, working_dir: Path, pre_script: str | None = None,
                              post_script: str | None = None, print_output: bool = True, use_fakeroot: bool = False):
        """
        Call a function in the package script, if it exists. If the function does not exist, this will do nothing.

        Args:
            function_name (str): The name of the function inside the package script to call
            working_dir (str): The working directory to execute the function in
            pre_script (str | None, optional): Additional script to run before the function call. Defaults to None.
            post_script (str | None, optional): Additional script to run after the function call. Defaults to None.
            print_output (bool, optional): Whether to print the output of the function. Defaults to True.
            use_fakeroot (bool, optional): Whether to use fakeroot for the command. Defaults to False.
        """

        logger.verbose(f"Calling function {function_name} in package script from {working_dir}")

        ShellCommand.exec(
            configuration=self.configuration,
            command=f'''
                source {self.recipe_path}

                {pre_script if pre_script else ''}

                if declare -F {function_name} >/dev/null; then
                    {function_name};
                else
                    echo 'Skipping "{function_name}". Function not found.';
                fi

                {post_script if post_script else ''}
            ''',
            working_directory=working_dir,
            environment=self._get_environment_variables(self.description.name, str(self.description.version), self.description.release),
            print_output=print_output,
            throw_on_error=True,
            use_fakeroot=use_fakeroot
        )

    def _get_environment_variables(self, name: str|None, version: str|None, release: str|None) -> dict[str, str]:
        """
        Get the environment variables for the recipe.
        This can be used to pass additional variables to the package script.

        Returns:
            dict[str, str]: The environment variables for the recipe.
        """

        env = {
            "alpaca_build": "1",
            "alpaca_version": __version__,
            "source_directory": join(self.source_directory),
            "build_directory": join(self.build_directory),
            "package_directory": join(self.package_directory),
            "target_architecture": self.configuration.target_architecture,
            "target_platform": "linux",
            "c_flags": self.configuration.c_flags,
            "cpp_flags": self.configuration.cpp_flags,
            "ld_flags": self.configuration.ld_flags,
            "make_flags": self.configuration.make_flags,
            "ninja_flags": self.configuration.ninja_flags
        }

        if name is not None:
            env.update({"name": name})

        if version is not None:
            env.update({"version": version})

        if release is not None:
            env.update({"release": release})

        return env

    def _download_source_file(self, source: str, sha256sum: str) -> str:
        """
        Download a source file to the source directory and verify the sha256 sum.

        Args:
            source (str): The path or url of the source file
            sha256sum (str): The expected sha256 sum of the source file

        Raises:
            ValueError: If the source file does not exist or the sha256 sum does not match

        Returns:
            str: The full path to the downloaded file
        """

        logger.info(f"Downloading source {source} to {self.source_directory}")

        # If the source is a URL
        if urlparse(source).scheme != "":
            logger.verbose(f"Source {source} is a URL. Downloading.")
            download_file(self.configuration, source, self.source_directory,
                          show_progress=self.configuration.show_download_progress)
        # If not, check if it is a full path
        elif isfile(source):
            logger.verbose(f"Source {source} is a direct path. Copying.")
            shutil.copy(source, self.source_directory)
        # If not, look relative to the package directory
        elif isfile(join(self.recipe_directory, source)):
            logger.verbose(f"Source {source} is relative to the recipe directory")
            shutil.copy(join(self.recipe_directory, source), self.source_directory, )

        file_path = join(self.source_directory, basename(source))

        # Check the hash of the file
        if not check_file_hash_from_string(file_path, sha256sum):
            raise ValueError(f"Source {source} hash mismatch. Expected {sha256sum}")

        return file_path
