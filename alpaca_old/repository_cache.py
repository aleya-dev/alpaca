from enum import Enum
from os import makedirs
from os.path import exists, join
from pathlib import Path
from shutil import rmtree
from tarfile import open as tarfile_open

from alpaca.atom import decompose_package_atom_from_name
from alpaca.common.file_downloader import download_file
from alpaca.common.hash import check_file_hash_from_file
from alpaca.common.logging import logger
from alpaca.common.shell_command import ShellCommand
from alpaca.configuration import Configuration
from alpaca.recipe_version import RecipeVersion
from alpaca.repository_ref import RepositoryType, RepositoryRef


class RepositorySearchType(Enum):
    """
    Enum representing the type of repository search.
    """

    RECIPE = "recipe"  # Search for recipes in the repository cache (typically during a build).
    PACKAGE_INFO = "package_info"  # Search for package_info files in the repository cache (for package installation and dependency resolution).


class _PackageCandidate:
    def __init__(self, version: RecipeVersion, path: Path):
        self.version: RecipeVersion = version
        self.path: Path = path


class RepositoryCache:
    def __init__(self, configuration: Configuration):
        self.configuration = configuration

    def update_cache(self):
        """
        Update the repository cache based on the current configuration.
        This method should be implemented to update the cache as needed.
        """

        self._ensure_repository_cache_path_exists()

        for repo_ref in self.configuration.repositories:
            if repo_ref.type == RepositoryType.GIT:
                self._update_git_cache(repo_ref)
            elif repo_ref.type == RepositoryType.WEB:
                self._update_web_cache(repo_ref)
            elif repo_ref.type == RepositoryType.LOCAL:
                logger.debug(f"Skipping local repository cache update for {repo_ref}")
            else:
                raise ValueError(f"Unsupported repository type: {repo_ref.type}")

    def reset_cache(self):
        """
        Reset the repository cache by removing all cached repositories and redownloading them.
        """

        for repo_ref in self.configuration.repositories:
            if repo_ref.type != RepositoryType.GIT:
                continue

            repository_path = repo_ref.get_cache_path(self.configuration.repository_cache_path)
            if exists(repository_path):
                rmtree(repository_path)

            self._update_git_cache(repo_ref)

    def find_by_path(self, path: str, search_type: RepositorySearchType) -> Path | None:
        """
        Find a path to a recipe for the given search string in the repository cache.

        Args:
            path (str): The path or name of the package to find.
            search_type (RepositorySearchType): The type of search to perform (recipe or package_info).
        """
        if not exists(self.configuration.repository_cache_path):
            raise ValueError(
                f"Repository cache path '{self.configuration.repository_cache_path}' does not exist. "
                "Please run 'apupdate' to create the cache."
            )

        if path == "":
            logger.error("No package name given.")
            return None

        if exists(path):
            logger.debug("Given package detected as absolute path.")
            return Path(path)

        logger.debug("Given package detected as name.")
        return self._find_by_name(path, search_type)

    def _find_by_name(self, name: str, search_type: RepositorySearchType) -> Path | None:
        """
        Find a recipe or package_info path by name in the repository cache.

        Args:
            name (str): The name of the package to search for
            search_type (RepositorySearchType): The type of search to perform (recipe or package_info).

        Returns:
            Path | None: The path to the recipe or package_info file if found, otherwise None.
        """

        name, requested_version = decompose_package_atom_from_name(name)
        candidates: list[_PackageCandidate] = []

        file_extension = \
            self.configuration.recipe_file_extension \
                if search_type == RepositorySearchType.RECIPE else self.configuration.package_info_file_extension
        search_name = "recipe" if search_type == RepositorySearchType.RECIPE else "package info"

        if len(self.configuration.repositories) == 0:
            raise Exception("No repositories configured. Please add repositories to the configuration.")

        for repo_ref in self.configuration.repositories:
            repo_path = repo_ref.get_cache_path(self.configuration.repository_cache_path)

            logger.verbose(f"Repository {repo_ref.path}")

            for stream in self.configuration.package_streams:
                logger.verbose(f" - Searching '{stream}'...")

                package_path_base = join(repo_path, stream, name)

                if not exists(package_path_base):
                    continue

                logger.verbose(f"Searching for {search_name} in {package_path_base}")

                for recipe_file_path in Path(package_path_base).iterdir():
                    if not recipe_file_path.is_file():
                        logger.verbose(f"Skipping non-file: {recipe_file_path.name}")
                        continue

                    if not recipe_file_path.name.endswith(file_extension):
                        logger.verbose(f"Skipping file {recipe_file_path.name}. Not a {search_name} file.")
                        continue

                    version = recipe_file_path.name[len(name) + 1:][:-len(file_extension)]

                    if version == "":
                        logger.warning(
                            f"Found {search_name} {recipe_file_path} without version information. Skipping.")
                        continue

                    candidates.append(_PackageCandidate(RecipeVersion.from_string(version), recipe_file_path))

        if not candidates:
            logger.error(f"No {search_name} found for package '{name}' in the repository cache.")
            return None

        version = RecipeVersion.find_closest_version_or_none(
            versions=[c.version for c in candidates],
            requested_version=requested_version
        )

        if version is None:
            logger.error(
                f"No matching version found for {search_name} '{name}' with requested version '{requested_version}'.")
            return None

        for candidate in candidates:
            if candidate.version == version:
                logger.debug(f"Found {search_name} {candidate.path} for package '{name}' with version '{version}'")
                return candidate.path

        return None

    def _ensure_repository_cache_path_exists(self):
        if not exists(self.configuration.repository_cache_path):
            logger.info(f"Creating repository cache directory: {self.configuration.repository_cache_path}")
            makedirs(self.configuration.repository_cache_path, exist_ok=True)

    def _update_git_cache(self, repo_ref: RepositoryRef):
        """
        Update the cache for a git repository.

        Args:
            repo_ref (RepositoryRef): The reference to the git repository to update.
        """

        if repo_ref.type != RepositoryType.GIT:
            raise ValueError(f"Repository reference {repo_ref} is not a git repository.")

        repository_path = repo_ref.get_cache_path(self.configuration.repository_cache_path)

        logger.debug(f"Updating git repository cache for {repo_ref} on {repository_path}")

        if not exists(repository_path):
            if (
                    ShellCommand.exec(
                        configuration=self.configuration,
                        command=f"git clone {repo_ref.path} {repository_path}").error_code != 0):
                logger.error(f"Failed to clone repository {repository_path}")
                raise ValueError(f"Failed to clone repository {repository_path}")
        else:
            if ShellCommand.exec(
                    configuration=self.configuration,
                    command=f"git -C {repository_path} diff --quiet").error_code != 0:
                logger.error(
                    f"Local changes detected in repository {repository_path}. "
                    "Local changes in the cache are currently not supported. "
                    "Please remove them."
                )
                raise ValueError(f"Local changes detected in repository {repository_path}")

            if ShellCommand.exec(
                    configuration=self.configuration,
                    command=f"git -C {repository_path} pull --ff-only").error_code != 0:
                logger.error(f"Failed to update repository {repository_path}")
                raise ValueError(f"Failed to update repository {repository_path}")

    def _update_web_cache(self, repo_ref: RepositoryRef):
        """
        Update the cache for a web repository.

        Args:
            repo_ref (RepositoryRef): The reference to the web repository to update.
        """

        if repo_ref.type != RepositoryType.WEB:
            raise ValueError(f"Repository reference {repo_ref} is not a web repository.")

        repository_path = repo_ref.get_cache_path(self.configuration.repository_cache_path)
        logger.debug(f"Updating web repository cache for {repo_ref} on {repository_path}")

        if not exists(repository_path):
            logger.info(f"Creating repository cache directory: {repository_path}")
            makedirs(repository_path, exist_ok=True)

        for stream in self.configuration.package_streams:
            try:
                download_file(f"{repo_ref.path}/{stream}{self.configuration.package_database_extension}",
                              repository_path,
                              show_progress=self.configuration.show_download_progress)

                download_file(f"{repo_ref.path}/{stream}{self.configuration.package_database_extension}.sha256",
                              repository_path,
                              show_progress=self.configuration.show_download_progress)

                package_info_path = join(repository_path, f"{stream}{self.configuration.package_database_extension}")
                check_file_hash_from_file(package_info_path)

                stream_dir = join(repository_path, stream)

                if exists(stream_dir):
                    logger.verbose(f"Removing existing stream directory: {stream_dir}")
                    rmtree(stream_dir)

                logger.verbose(f"Extracting package info for stream '{stream}' to {repository_path}")
                with tarfile_open(package_info_path, "r:gz") as tar:
                    tar.extractall(path=repository_path)

                logger.info(
                    f"Downloaded package info for stream '{stream}' from {repo_ref.path} to {package_info_path}")
            except Exception as e:
                logger.warning(f"Could not download package info for stream '{stream}' from {repo_ref.path}: {e}")
                logger.warning("It could be that this repository does not have this particular stream.")
                continue
