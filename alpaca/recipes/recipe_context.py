import importlib.metadata
import shutil
from os.path import join, isfile, basename
from pathlib import Path
from tarfile import is_tarfile
from urllib.parse import urlparse

from alpaca.common.file_downloader import download_file
from alpaca.common.hash import check_file_hash_from_string
from alpaca.common.logging import logger
from alpaca.common.shell_command import ShellCommand
from alpaca.common.tar import extract_tar
from alpaca.configuration.configuration import Configuration
from alpaca.recipes.build_context import BuildContext

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
        self.build_context = BuildContext.create_from_recipe(configuration, path)

    def create_package(self):
        """
        Create the package by handling sources, building, checking, and packaging.

        This function will create a workspace directory structure, download sources, build the package,
        check the package, and finally package it into a tar.gz archive.
        """

        try:
            self.build_context.create_workspace_directories()
            self.build_context.write_build_context_json()
            self._handle_sources()
            self._handle_build()
            self._handle_check()
            self._handle_package()
        except Exception:
            raise
        finally:
            self.build_context.delete_workspace_directories()

    def _handle_sources(self):
        logger.info("Handle sources...")

        if len(self.build_context.description.sources) != len(self.build_context.description.sha256sums):
            raise Exception(f"Number of sources ({len(self.build_context.description.sources)}) does not match "
                            f"number of sha256sums ({len(self.build_context.description.sha256sums)})")

        if len(self.build_context.description.sources) == 0:
            return

        for source, sha256sum in zip(self.build_context.description.sources, self.build_context.description.sha256sums):
            filename = self._download_source_file(source, sha256sum)

            if is_tarfile(filename):
                logger.info(f"Extracting file {basename(filename)}...")
                extract_tar(Path(filename), self.build_context.source_directory)

        self._call_script_function(function_name="handle_sources", working_dir=self.build_context.source_directory)

    def _handle_build(self):
        """
        Build the package from source, if applicable. This function will call the handle_build function in the package
        script, if it exists. If the function does not exist, this will do nothing.
        """

        logger.info("Building package...")
        self._call_script_function(function_name="handle_build", working_dir=self.build_context.build_directory,
                                   print_output=not self.configuration.suppress_build_output)

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
        self._call_script_function(function_name="handle_check", working_dir=self.build_context.build_directory,
                                   print_output=not self.configuration.suppress_build_output)

    def _handle_package(self):
        """
        This function will call the handle_package function in the package script, if it exists.
        After that it will package the built package into a tar.xz archive to serve as the binary cache.
        """

        logger.info("Packaging package...")

        # TODO: Handle various config settings like verbose through environment variables so that when
        # apcommand runs, it can pick it up from the environment automatically.
        self._call_script_function(
            function_name="handle_package",
            working_dir=self.build_context.build_directory,
            post_script=f'apcommand {"--verbose" if self.configuration.verbose_output else ""} deploy {self.build_context.workspace_path} {self.configuration.package_artifact_path}',
            print_output=not self.configuration.suppress_build_output,
            use_fakeroot=True
        )

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

        ShellCommand.exec(configuration=self.configuration, command=f'''
                source {self.build_context.recipe_path}

                {pre_script if pre_script else ''}

                if declare -F {function_name} >/dev/null; then
                    {function_name};
                else
                    echo 'Skipping "{function_name}". Function not found.';
                fi

                {post_script if post_script else ''}
            ''', working_directory=working_dir,
                          environment=self.build_context.get_environment_variables(),
                          print_output=print_output,
                          throw_on_error=True, use_fakeroot=use_fakeroot)

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

        source_directory = self.build_context.source_directory

        logger.info(f"Downloading source {source} to {source_directory}")

        # If the source is a URL
        if urlparse(source).scheme != "":
            logger.verbose(f"Source {source} is a URL. Downloading.")
            download_file(self.configuration, source, source_directory,
                          show_progress=self.configuration.show_download_progress)
        # If not, check if it is a full path
        elif isfile(source):
            logger.verbose(f"Source {source} is a direct path. Copying.")
            shutil.copy(source, source_directory)
        # If not, look relative to the package directory
        elif isfile(join(self.build_context.recipe_directory, source)):
            logger.verbose(f"Source {source} is relative to the recipe directory")
            shutil.copy(join(self.build_context.recipe_directory, source), source_directory, )

        file_path = join(source_directory, basename(source))

        # Check the hash of the file
        if not check_file_hash_from_string(file_path, sha256sum):
            raise ValueError(f"Source {source} hash mismatch. Expected {sha256sum}")

        return file_path
