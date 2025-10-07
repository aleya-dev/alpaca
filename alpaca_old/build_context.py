from os import makedirs
from os.path import exists, join, isfile, basename
from pathlib import Path
from shutil import rmtree, copyfile, copy
from tarfile import is_tarfile
from urllib.parse import urlparse

from alpaca.common.call_script_function import call_script_function
from alpaca.common.file_downloader import download_file
from alpaca.common.hash import check_file_hash_from_string, write_file_hash
from alpaca.common.logging import logger
from alpaca.common.tar import extract_tar, compress_tar
from alpaca.package_file import PackageFile
from alpaca.package_file_info import write_file_info
from alpaca.recipe import Recipe


class BuildContext:
    def __init__(self, recipe: Recipe):
        self.recipe = recipe
        self._allow_workspace_cleanup = True

    @property
    def workspace_directory(self) -> Path:
        return Path(join(self.recipe.configuration.package_workspace_path, self.recipe.info.name,
                         str(self.recipe.info.version)))

    @property
    def source_directory(self) -> Path:
        """
        Get the path where the source files are located.
        """
        return Path(self.workspace_directory, "source")

    @property
    def build_directory(self) -> Path:
        """
        Get the path where the build files are located.
        """
        return Path(self.workspace_directory, "build")

    @property
    def package_directory(self) -> Path:
        """
        Get the path where the package files are located.
        """
        return Path(self.workspace_directory, "package")

    @property
    def package_file_path(self) -> Path:
        return Path(join(self.recipe.configuration.package_artifact_path, self.recipe.info.stream, self.recipe.info.name,
                         f"{self.recipe.info.name}-{self.recipe.info.version}-{self.recipe.info.release}{self.recipe.configuration.package_file_extension}"))

    def create_package(self) -> PackageFile:
        """
        Create the package by handling sources, building, checking, and packaging.

        This function will create a workspace directory structure, download sources, build the package,
        check the package, and finally package it into a tar.gz archive.
        """

        try:
            self._create_workspace_directories()
            self._write_workspace_files()
            self._handle_sources()
            self._handle_build()
            self._handle_check()
            self._handle_package()
        except Exception:
            raise
        finally:
            self._delete_workspace_directories()

        return PackageFile(self.package_file_path)

    def deploy_package(self) -> PackageFile:
        """
        Deploy the package to the specified output directory.

        This function will copy the built package to the output directory and return a PackageFile object
        representing the deployed package.
        """
        logger.debug(f"Deploying package from {self.package_directory} "
                     f"to {self.recipe.configuration.package_artifact_path}")

        write_file_info(self.package_directory)

        copyfile(self.recipe.info.path, join(self.package_directory, ".package_info"))
        copyfile(self.recipe.path, join(self.package_directory, ".recipe"))

        #join(self.package_directory, ".package_info")
        output_directory = join(self.recipe.configuration.package_artifact_path, self.recipe.info.stream,
            self.recipe.info.name)

        if not exists(output_directory):
            makedirs(output_directory)

        copyfile(self.recipe.info.path, join(output_directory,
            f"{self.recipe.info.file_atom}{self.recipe.configuration.package_info_file_extension}"))

        output_filename = self.package_file_path

        compress_tar(self.package_directory, output_filename)
        write_file_hash(output_filename)

        return PackageFile(output_filename)

    def _create_workspace_directories(self):
        self._allow_workspace_cleanup = False

        workspace_directory = self.workspace_directory

        if exists(workspace_directory):
            if self.recipe.configuration.package_delete_workspace:
                logger.verbose(f"Removing existing workspace {workspace_directory}")
                rmtree(workspace_directory)
            else:
                raise Exception(f"Workspace '{workspace_directory}' must not exist. "
                                "If you wish to delete it, you can use the --delete-workdir option.")

        logger.debug("Creating workspace directories: %s", workspace_directory)

        makedirs(workspace_directory)
        makedirs(self.source_directory)
        makedirs(self.build_directory)
        makedirs(self.package_directory)

        self._allow_workspace_cleanup = True

    def _write_workspace_files(self):
        self.recipe.info.write_json(join(self.workspace_directory, ".package_info"))
        copyfile(self.recipe.path, join(self.workspace_directory, ".recipe"))

    def _delete_workspace_directories(self):
        """
        Clean up the workspace directories created for this recipe context.
        This will remove the source, build, and package directories.
        """

        if not self._allow_workspace_cleanup:
            return

        if not exists(self.workspace_directory):
            return

        if not self.recipe.configuration.keep_build_directory:
            logger.info("Cleaning up build directories...")
            rmtree(self.workspace_directory)
        else:
            logger.info("Keeping build directories...")

    def _handle_sources(self):
        logger.info("Handle sources...")

        if len(self.recipe.sources) > 0:
            for source, sha256sum in zip(self.recipe.sources,
                                         self.recipe.sha256sums):
                filename = self._download_source_file(source, sha256sum)

                if is_tarfile(filename):
                    logger.info(f"Extracting file {basename(filename)}...")
                    extract_tar(Path(filename), self.source_directory)

        call_script_function(
            configuration=self.recipe.configuration,
            recipe_path=self.recipe.path,
            function_name="handle_sources",
            working_dir=self.source_directory,
            environment=self._get_environment_variables()
        )

    def _handle_build(self):
        """
        Build the package from source, if applicable. This function will call the handle_build function in the package
        script, if it exists. If the function does not exist, this will do nothing.
        """

        logger.info("Building package...")
        call_script_function(
            configuration=self.recipe.configuration,
            recipe_path=self.recipe.path,
            function_name="handle_build",
            working_dir=self.build_directory,
            environment=self._get_environment_variables(),
            print_output=not self.recipe.configuration.suppress_build_output
        )

    def _handle_check(self):
        """
        Check the package after building; typically this runs tests to ensure the package is built correctly.
        Not all packages have tests. It is up to the package maintainer to implement this function or not in
        the recipe.

        This function will call the handle_check function in the package script, if it exists. If the function does not
        exist, this will do nothing.
        """

        if self.recipe.configuration.skip_package_check:
            logger.warning(
                "Skipping package check. This can lead to unexpected behavior as packages may not be built correctly.")
            return

        logger.info("Checking package...")
        call_script_function(
            configuration=self.recipe.configuration,
            recipe_path=self.recipe.path,
            function_name="handle_check",
            working_dir=self.build_directory,
            environment=self._get_environment_variables(),
            print_output=not self.recipe.configuration.suppress_build_output
        )

    def _handle_package(self):
        """
        This function will call the handle_package function in the package script, if it exists.
        After that it will package the built package into a tar.xz archive to serve as the binary cache.
        """

        logger.info("Packaging package...")
        call_script_function(
            configuration=self.recipe.configuration,
            recipe_path=self.recipe.path,
            function_name="handle_package",
            working_dir=self.build_directory,
            environment=self._get_environment_variables(),
            post_script=
            f'apcommand deploy {self.workspace_directory} {self.recipe.configuration.package_artifact_path}',
            print_output=not self.recipe.configuration.suppress_build_output,
            use_fakeroot=True
        )

    def _get_environment_variables(self) -> dict[str, str]:
        """
        Get the environment variables for the recipe.
        This can be used to pass additional variables to the package script.

        Returns:
            dict[str, str]: The environment variables for the recipe.
        """

        env = self.recipe.configuration.get_environment_variables()
        env.update(self.recipe.info.get_environment_variables())

        env.update({
            "source_directory": str(self.source_directory),
            "build_directory": str(self.build_directory),
            "package_directory": str(self.package_directory)
        })

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
        source_directory = self.source_directory

        logger.info(f"Downloading source {source} to {source_directory}")

        # If the source is a URL
        if urlparse(source).scheme != "":
            logger.verbose(f"Source {source} is a URL. Downloading.")
            download_file(source, source_directory, show_progress=self.recipe.configuration.show_download_progress)
        # If not, check if it is a full path
        elif isfile(source):
            logger.verbose(f"Source {source} is a direct path. Copying.")
            copy(source, source_directory)
        # If not, look relative to the package directory
        elif isfile(join(self.recipe.recipe_directory, source)):
            logger.verbose(f"Source {source} is relative to the recipe directory")
            copy(join(self.recipe.recipe_directory, source), source_directory)

        file_path = join(source_directory, basename(source))

        # Check the hash of the file
        if not check_file_hash_from_string(file_path, sha256sum):
            raise ValueError(f"Source {source} hash mismatch. Expected {sha256sum}")

        return file_path
