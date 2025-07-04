from os import makedirs
from os.path import exists, join
from pathlib import Path
from shutil import rmtree

from alpaca.common.logging import logger
from alpaca.common.shell_command import ShellCommand
from alpaca.configuration.configuration import Configuration
from alpaca.configuration.repository_ref import RepositoryType
from alpaca.recipes.recipe_version import RecipeVersion


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
            if repo_ref.get_type() == RepositoryType.GIT:
                self._update_git_cache(repo_ref)
            elif repo_ref.get_type() == RepositoryType.LOCAL:
                logger.debug(f"Skipping local repository cache update for {repo_ref}")
            else:
                raise ValueError(f"Unsupported repository type: {repo_ref.get_type()}")

    def reset_cache(self):
        """
        Reset the repository cache by removing all cached repositories and redownloading them.
        """

        for repo_ref in self.configuration.repositories:
            if repo_ref.get_type() != RepositoryType.GIT:
                continue

            repository_path = repo_ref.get_cache_path(self.configuration.repository_cache_path)
            if exists(repository_path):
                rmtree(repository_path)

            self._update_git_cache(repo_ref)

    def find_recipe(self, path: str) -> Path | None:
        """
        Find a recipe for the given search string in the repository cache.
        This method should be implemented to search for recipes in the cache.

        Args:
            path (str): The path or name of the package to find.
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
        return self._find_recipe_by_name(path)

    def _find_recipe_by_name(self, name: str) -> Path | None:
        parts = name.split('/')

        if len(parts) > 2:
            raise ValueError("Invalid package name format. Expected format: <name> or <name>/<version>")

        name = parts[0]

        requested_version: str | None = None

        if len(parts) == 2:
            requested_version = parts[1]
 
        candidates : list[_PackageCandidate] = []

        if len(self.configuration.repositories) == 0:
            raise Exception("No repositories configured. Please add repositories to the configuration.")

        for repo_ref in self.configuration.repositories:
            repo_path = repo_ref.get_cache_path(self.configuration.repository_cache_path)

            logger.verbose(f"Repository {repo_ref.get_path()}")

            for stream in self.configuration.package_streams:
                logger.verbose(f" - Searching '{stream}'...")

                package_path_base = join(repo_path, stream, name)

                if not exists(package_path_base):
                    continue

                logger.verbose(f"Searching for recipes in {package_path_base}")

                for recipe_file_path in Path(package_path_base).iterdir():
                    if not recipe_file_path.is_file():
                        logger.verbose(f"Skipping non-file: {recipe_file_path.name}")
                        continue

                    if not recipe_file_path.name.endswith(self.configuration.recipe_file_extension):
                        logger.verbose(f"Skipping non-recipe file: {recipe_file_path.name}")
                        continue

                    version = recipe_file_path.name[len(name)+1:][:-len(self.configuration.recipe_file_extension)]

                    if version == "":
                        logger.warning(f"Found recipe {recipe_file_path} without version information. Skipping.")
                        continue

                    candidates.append(_PackageCandidate(RecipeVersion.from_string(version), recipe_file_path))

        if not candidates:
            logger.error(f"No recipes found for package '{name}' in the repository cache.")
            return None

        version = RecipeVersion.find_closest_version_or_none(
            versions=[c.version for c in candidates],
            requested_version=requested_version
        )

        if version is None:
            logger.error(f"No matching version found for package '{name}' with requested version '{requested_version}'.")
            return None

        for candidate in candidates:
            if candidate.version == version:
                logger.debug(f"Found recipe {candidate.path} for package '{name}' with version '{version}'")
                return candidate.path

        return None


    def _ensure_repository_cache_path_exists(self):
        if not exists(self.configuration.repository_cache_path):
            logger.info(f"Creating repository cache directory: {self.configuration.repository_cache_path}")
            makedirs(self.configuration.repository_cache_path, exist_ok=True)

    def _update_git_cache(self, repo_ref):
        """
        Update the cache for a git repository.
        This method should be implemented to handle git repository updates.
        """
        repository_path = repo_ref.get_cache_path(self.configuration.repository_cache_path)

        logger.debug(f"Updating git repository cache for {repo_ref} on {repository_path}")

        if not exists(repository_path):
            if (
                ShellCommand.exec(
                    configuration=self.configuration,
                    command=f"git clone {repo_ref.get_path()} {repository_path}").error_code != 0):
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
