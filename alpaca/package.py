from alpaca.logging import logger
from alpaca.configuration import Configuration
from alpaca.shell_command import ShellCommand
from alpaca.package_description import PackageDescription, Atom
from alpaca.utils import (
    is_url,
    is_file_path,
    download_file,
    check_file_hash_from_string,
    check_file_hash_from_file,
    create_empty_directory,
    is_tarfile,
    extract_tar,
    compress_tar,
    write_file_hash,
)
import hashlib
import os
import shutil


class Package:
    def __init__(self, atom_info: Atom, path: str):
        """
        Create a new package object

        Args:
            path (str): The path to the package recipe file. Preferably an absolute path.
        """

        self.description: PackageDescription = PackageDescription.Load(atom_info, path)
        self.options: dict[str, bool] = {}

    def print_info(self):
        """
        Print information about the package to the logger
        """

        logger.info("Package Information")
        logger.info(f"  Name: {self.description.atom.name}")
        logger.info(f"  Atom: {self.description.atom}")
        logger.info(f"  URL: {self.description.url}")
        logger.info(f"  Licenses: {self.description.licenses}")
        logger.info(f"  Dependencies: {self.description.dependencies}")
        logger.info(f"  Build Dependencies: {self.description.build_dependencies}")
        logger.info(f"  Sources: {self.description.sources}")
        logger.info(f"  SHA256 Sums: {self.description.sha256sums}")
        logger.info(f"  Available options: {self.description.available_options}")
        logger.info("")
        logger.info("Package Configuration")
        logger.info(f"  Options: {self.options}")
        logger.info(f"  Binary Hash: {self._compute_binary_hash()}")

    def build(self):
        """
        Build, check and deploy the package according to the recipe.
        If a prebuilt binary is available, this will be used instead of building from source.
        In that case the build, check and package functions will be skipped.
        """

        logger.info(f"Building package {self.description.atom}...")

        config = Configuration()

        self._create_working_directories()

        if config.force_build_from_source:
            logger.info("Forcing build from source. Ignoring binary cache.")

        require_build = config.force_build_from_source

        artifact_file_path = self._get_binary_archive_path()

        if not require_build:
            if os.path.exists(artifact_file_path):
                logger.info("Binary cache found...")
                if check_file_hash_from_file(artifact_file_path):
                    logger.info("Binary cache hash matches. Skipping build.")
                else:
                    logger.info("Binary cache hash mismatch. Rebuilding...")
                    require_build = True
            else:
                logger.info("Binary cache not found. Rebuilding...")
                require_build = True

        if not require_build:
            extract_tar(artifact_file_path, self._get_package_package_directory())
        else:
            if config.install_target != "/":
                raise ValueError(
                    "Binary cache for this install is required, but a binary cache was not found for this package."
                )

            try:
                self._create_working_directories()
                self._handle_sources()
                self._handle_build()
                self._handle_check()
                self._handle_package()
                self._compress_package()
            except Exception:
                logger.error("Failed to build package...")
                logger.verbose("Stacktrace: ", exc_info=True)

                if not config.keep_intermediates_on_failure:
                    self._cleanup_working_directories()

                raise ValueError("Failed to build package")

        try:
            self._generate_package_metadata()
            self._install_to_system()
            self._handle_post_install()
        except Exception:
            logger.error("Failed to install package...")
            logger.verbose("Stacktrace: ", exc_info=True)

            if not config.keep_intermediates_on_failure:
                self._cleanup_working_directories()

            raise ValueError("Failed to install package")
        finally:
            self._cleanup_working_directories()

    def _get_package_workdir_base_path(self) -> str:
        return os.path.join(
            Configuration().get_workspace_base_path(),
            self.description.atom.name,
            f"{self.description.atom.version}-{self.description.atom.release}",
        )

    def _get_package_source_directory(self) -> str:
        return os.path.join(self._get_package_workdir_base_path(), "source")

    def _get_package_build_directory(self) -> str:
        return os.path.join(self._get_package_workdir_base_path(), "build")

    def _get_package_package_directory(self) -> str:
        return os.path.join(self._get_package_workdir_base_path(), "package")

    def get_package_local_binary_cache_base_path(self) -> str:
        return os.path.join(
            Configuration().get_package_local_binary_cache_base_path(),
            self.description.atom.name,
            f"{self.description.atom.version}-{self.description.atom.release}",
        )

    def _get_binary_archive_path(self) -> str:
        return os.path.join(
            self.get_package_local_binary_cache_base_path(),
            f"{self._compute_binary_hash()}.tar.xz",
        )

    def _create_working_directories(self):
        """
        Create the working directories for the package where needed.
        This includes the source, build, package and artifact directories
        """
        package_workdir_base_path = self._get_package_workdir_base_path()

        os.makedirs(package_workdir_base_path, exist_ok=True)

        # Remove the source directory
        if os.path.exists(self._get_package_source_directory()):
            shutil.rmtree(self._get_package_source_directory())

        create_empty_directory(self._get_package_source_directory())
        create_empty_directory(self._get_package_build_directory())
        create_empty_directory(self._get_package_package_directory())

        # The artifact directory is not removed, as it is used to store the final packages
        os.makedirs(self.get_package_local_binary_cache_base_path(), exist_ok=True)

    def _handle_sources(self):
        """
        Download/Copy and where possible, extract the source files for the package.
        This function will also call the handle_sources function in the package script, if it exists.
        """

        logger.info("Handle sources...")

        for i in range(len(self.description.sources)):
            filename = self._download_source_file(
                self.description.sources[i], self.description.sha256sums[i]
            )

            if is_tarfile(filename):
                logger.info(f"Extracting file {os.path.basename(filename)}...")
                extract_tar(filename, self._get_package_source_directory())

        self._call_script_function(
            "handle_sources", self._get_package_source_directory()
        )

    def _handle_build(self):
        """
        Build the package from source, if applicable. This function will call the handle_build function in the package
        script, if it exists. If the function does not exist, this will do nothing.
        """

        logger.info("Building package...")
        self._call_script_function(
            "handle_build",
            self._get_package_build_directory(),
            print_output=not Configuration().suppress_build_output,
        )

    def _handle_check(self):
        """
        Check the package after building; typically this runs tests to ensure the package is built correctly.
        Not all packages have tests. It is up to the package maintainer to implement this function or not in
        the recipe.

        This function will call the handle_check function in the package script, if it exists. If the function does not
        exist, this will do nothing.
        """

        config = Configuration()

        if config.skip_check:
            logger.warning(
                "--no-check used. Skipping package check. "
                "This can lead to unexpected behavior as packages may not be built correctly."
            )
            return

        logger.info("Checking package...")
        self._call_script_function(
            "handle_check",
            self._get_package_build_directory(),
            print_output=not config.suppress_build_output,
        )

    def _handle_package(self):
        """
        This function will call the handle_package function in the package script, if it exists.
        After that it will package the built package into a tar.xz archive to serve as the binary cache.
        """

        logger.info("Packaging package...")
        self._call_script_function(
            "handle_package",
            self._get_package_build_directory(),
            print_output=not Configuration().suppress_build_output,
        )

    def _generate_package_metadata(self):
        """
        Generate metadata for the package. This will include the package name, version and release.
        This way the package can be identified and managed by the package manager, even when the
        repository is not available.
        """

        config = Configuration()

        if config.is_dry_run:
            logger.warning("Dry run enabled. Skipping metadata generation.")
            return

        package_metadata_directory = os.path.join(
            config.install_target,
            "var",
            "lib",
            "alpaca",
            "packages",
            f"{self.description.atom.name}",
        )

        os.makedirs(package_metadata_directory, exist_ok=True)

        package_files = []
        for root, _, files in os.walk(self._get_package_package_directory()):
            for file in files:
                package_files.append(
                    os.path.relpath(
                        os.path.join(root, file), self._get_package_package_directory()
                    )
                )

        # Write the list to a text file
        with open(os.path.join(package_metadata_directory, "files"), "w") as file:
            for package_file in package_files:
                file.write(f"/{package_file}\n")

        shutil.copy(self.description.recipe_path, package_metadata_directory)

    def _compress_package(self):
        """
        Compress the package directory into a tar.xz archive and store it in the local binary cache.
        """

        output_archive_file = os.path.join(
            self.get_package_local_binary_cache_base_path(),
            f"{self._compute_binary_hash()}.tar.xz",
        )

        compress_tar(self._get_package_package_directory(), output_archive_file)
        write_file_hash(output_archive_file)

    def _install_to_system(self):
        """
        Install the package to the system. This will copy the package directory to the install target.
        By default this is the system root directory ('/'), but this can be changed on the commandline.
        """

        config = Configuration()

        if config.is_dry_run:
            logger.warning("Dry run enabled. Skipping installation.")
            return

        if not config.is_aleya_linux_host and config.install_target == "/":
            logger.warning(
                "Not running on an Aleya Linux host. Physically installing packages to '/' will be skipped."
            )
            return

        logger.info("Installing package to system...")

        shutil.copytree(
            self._get_package_package_directory(),
            config.install_target,
            dirs_exist_ok=True,
            symlinks=True,
        )

    def _handle_post_install(self):
        """
        This function will call the handle_post_install function in the package script, if it exists.
        If the function does not exist, this will do nothing.
        """

        config = Configuration()

        if config.is_dry_run:
            logger.warning("Dry run enabled. Skipping post-install script.")
            return

        if config.install_target != "/":
            logger.warning(
                "Custom install target is set. Skipping post-install script."
            )
            return

        if not Configuration().is_aleya_linux_host:
            logger.warning(
                "Not running on an Aleya Linux host. Skipping post-install script."
            )
            return

        logger.info("Running post-install script...")
        self._call_script_function(
            "handle_post_install", self._get_package_package_directory()
        )

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

        source_path = self._get_package_source_directory()

        logger.info(f"Downloading source {source} to {source_path}")

        config = Configuration()

        # If the source is a URL
        if is_url(source):
            logger.verbose(f"Source {source} is a URL")
            download_file(
                source, source_path, show_progress=config.show_download_progress
            )
        # If not, check if it is a full path
        elif is_file_path(source):
            logger.verbose(f"Source {source} is a direct path")
            shutil.copy(source, source_path)
        # If not, look relative to the package directory
        elif is_file_path(
            os.path.join(self.description.get_recipe_directory(), source)
        ):
            logger.verbose(f"Source {source} is relative to the recipe directory")
            shutil.copy(
                os.path.join(self.description.get_recipe_directory(), source),
                source_path,
            )
        # If not, look relative to all the repositories, in order
        else:
            found = False
            for repo in config.repositories:
                repo_path = os.path.join(repo, source)
                if is_file_path(repo_path):
                    logger.verbose(
                        f"Source {source} is relative to the repository {repo}"
                    )
                    shutil.copy(repo_path, source_path)
                    found = True
                    break

            if not found:
                raise ValueError(f"Source {source} is not a valid URL or file path")

        file_path = os.path.join(source_path, os.path.basename(source))

        # Check the hash of the file
        if not check_file_hash_from_string(file_path, sha256sum):
            raise ValueError(f"Source {source} hash mismatch. Expected {sha256sum}")

        return file_path

    def _call_script_function(
        self, function_name: str, working_dir: str, print_output: bool = True
    ):
        """
        Call a function in the package script, if it exists. If the function does not exist, this will do nothing.

        Args:
            function_name (str): The name of the function inside of the package script to call
            working_dir (str): The working directory to execute the function in
            print_output (bool, optional): Whether to print the output of the function. Defaults to True.
        """

        logger.verbose(
            f"Calling function {function_name} in package script from {working_dir}"
        )

        ShellCommand.exec(
            f"source {self.description.recipe_path} && "
            f"(if declare -F {function_name} >/dev/null; then "
            f"{function_name}; else "
            f"echo 'Skipping \"{function_name}\". Function not found.'; fi)",
            working_directory=working_dir,
            environment=self._get_environment_variables(),
            print_output=print_output,
            throw_on_error=True,
        )

    def _get_environment_variables(self) -> dict[str, str]:
        """
        Create a dictionary of environment variables to pass to the package script

        Returns:
            dict[str, str]: A dictionary of environment variables to be passed to the package script
        """

        config = Configuration()
        env = {}

        for key in self.options.keys():
            env[f"option_{key.lower()}"] = "1"

        env["working_directory"] = self._get_package_workdir_base_path()
        env["source_directory"] = self._get_package_source_directory()
        env["build_directory"] = self._get_package_build_directory()
        env["package_directory"] = self._get_package_package_directory()
        env["target_architecture"] = config.target_architecture
        env["target_platform"] = "aleya-linux-gnu"
        env["package_atom"] = str(self.description.atom)
        env["package_version"] = self.description.atom.version
        env["package_build"] = self.description.atom.release

        env["c_flags"] = config.c_flags
        env["cpp_flags"] = config.cpp_flags
        env["ld_flags"] = config.ld_flags
        env["make_flags"] = config.make_flags
        env["ninja_flags"] = config.ninja_flags

        return env

    def _compute_binary_hash(self) -> str:
        """
        Compute a hash of the package script and options to determine if a prebuilt binary is available
        This can be used to skip building from source if the binary is already available

        Returns:
            str: The hash of the package script and options
        """

        with open(self.description.recipe_path, "r") as file:
            package_script = file.read()

        hash_object = hashlib.sha256()
        hash_object.update(package_script.encode("utf-8"))
        hash_object.update(Configuration().target_architecture.encode("utf-8"))

        for key in sorted(self.options.keys()):
            hash_object.update(key.encode("utf-8"))
            hash_object.update(str(self.options[key]).encode("utf-8"))

        return hash_object.hexdigest()

    def _cleanup_working_directories(self):
        """
        Cleanup the working directories for the package
        """

        logger.info("Cleaning up working directories")

        shutil.rmtree(self._get_package_workdir_base_path())

        parent_dir = os.path.join(
            Configuration().get_workspace_base_path(), self.description.atom.name
        )

        if not os.listdir(parent_dir):
            shutil.rmtree(parent_dir)
