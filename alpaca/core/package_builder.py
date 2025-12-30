from importlib import resources
from os import environ
from os.path import basename, isfile, join
from pathlib import Path
from shutil import copy, rmtree
from tarfile import is_tarfile
from urllib.parse import urlparse

from alpaca.core.alpaca_error import AlpacaError
from alpaca.core.configuration import Configuration
from alpaca.core.common.file_downloader import download_file
from alpaca.core.common.hash import check_file_hash_from_string
from alpaca.core.package_file_info import write_file_info
from alpaca.core.common.shell_command import ShellCommand
from alpaca.core.common.tar import extract_tar, compress_tar
from alpaca.core.recipe_info import RecipeInfo
from alpaca.core.common.logging import get_logger

logger = get_logger(__name__)


class PackageBuildError(AlpacaError):
    pass


class PackageBuilder:
    def __init__(self, recipe: RecipeInfo, config: Configuration):
        self.recipe = recipe
        self._config = config

    @property
    def source_directory(self) -> Path:
        return Path.cwd() / 'source'

    @property
    def build_directory(self) -> Path:
        return Path.cwd() / 'build'

    @property
    def package_directory(self) -> Path:
        return Path.cwd() / 'package'

    def ensure_directories(self, keep_source: bool = False, delete_if_exists: bool = False):
        if not keep_source:
            PackageBuilder._check_directory(self.source_directory, delete_if_exists=delete_if_exists)
        PackageBuilder._check_directory(self.build_directory, delete_if_exists=delete_if_exists)
        PackageBuilder._check_directory(self.package_directory, delete_if_exists=delete_if_exists)

    def handle_sources(self, keep_source: bool = False, skip_hash_check: bool = False):
        logger.header(f"Downloading sources for recipe {self.recipe.name}")

        if keep_source:
            logger.info("Skipping source download and copy step")
        else:
            if len(self.recipe.sources) > 0:
                for source, sha256sum in zip(self.recipe.sources,
                                             self.recipe.sha256sums):

                    filename = self._download_source_file(source, sha256sum, skip_hash_check=skip_hash_check)

                    if is_tarfile(filename):
                        logger.info(f"Extracting file {basename(filename)}...")
                        extract_tar(Path(filename), self.source_directory)

        self._call_script_function("sources", working_directory=self.source_directory)

    def build(self, quiet: bool = False):
        logger.header(f"Building packages for recipe {self.recipe.name}")

        self._call_script_function("build", working_directory=self.build_directory, print_output=not quiet)

        copy(self.recipe.path, self.package_directory / '.recipe')
        self.recipe.write_to_file(self.package_directory / ".recipe_info")

    def check(self, quiet: bool = False):
        logger.header(f"Checking build for recipe {self.recipe.name}")
        self._call_script_function("check", working_directory=self.build_directory, print_output=not quiet)

    def package(self, package_name: str, delete_if_exists: bool = False):
        logger.header(f"Packaging package {package_name} for recipe {self.recipe.name}")

        if package_name not in self.recipe.provides:
            raise PackageBuildError(f"Package {package_name} is not provided by the recipe {self.recipe.name}")

        package_directory = self.package_directory / f"{package_name}-{self.recipe.version}-{self.recipe.build}"

        PackageBuilder._check_directory(package_directory, delete_if_exists=delete_if_exists)

        self._call_script_function(f"package_{package_name.replace("-", "_")}", use_fakeroot=True,
                                   working_directory=self.build_directory,
                                   additional_variables={"package_directory": str(package_directory)})

        write_file_info(package_directory, package_directory / ".file_info")
        copy(self.package_directory / '.recipe', package_directory / '.recipe')
        copy(self.package_directory / '.recipe_info', package_directory / '.recipe_info')

        compress_tar(package_directory, Path.cwd() / f"{package_name}-{self.recipe.version}-{self.recipe.build}.package.tar.xz")

    @staticmethod
    def _check_directory(path: Path, delete_if_exists: bool):
        if path.exists() and not delete_if_exists:
            raise PackageBuildError(f"Directory {path} already exists.")

        if path.exists() and delete_if_exists:
            logger.verbose(f"Removing existing directory {path}")
            rmtree(path)

        path.mkdir(parents=True, exist_ok=False)

    def _download_source_file(self, source: str, sha256sum: str, skip_hash_check: bool = False) -> str:
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
            download_file(source, source_directory, show_progress=True)
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
        if not skip_hash_check:
            if not check_file_hash_from_string(file_path, sha256sum):
                raise ValueError(f"Source {source} hash mismatch. Expected {sha256sum}")

        return file_path

    def _call_script_function(self,
                              function_name: str,
                              use_fakeroot=False,
                              print_output: bool = True,
                              working_directory: Path | None = None,
                              additional_variables: dict[str, str] | None = None):
        logger.verbose(f"Calling script function {function_name} from recipe {self.recipe.path}")

        variables = self._get_variables()

        if additional_variables is not None:
            variables.update(additional_variables)

        template_text = resources.read_text("alpaca.core.scripts", "call_recipe_function.sh")
        template_text = template_text.replace("@ALPACA_VARIABLES@", self._generate_variables_string(variables))

        ShellCommand.exec([template_text, "_", self.recipe.path, function_name],
                          print_output=print_output, throw_on_error=True,
                          working_directory=working_directory,
                          use_fakeroot=use_fakeroot)

    def _get_variables(self) -> dict[str, str]:
        variables = self._config.get_variables()
        variables.update(self.recipe.get_variables())

        variables.update({
            "source_directory": str(self.source_directory),
            "build_directory": str(self.build_directory)
        })

        return variables

    @staticmethod
    def _generate_variables_string(variables: dict[str, str]) -> str:
        variables_string = ""

        for key, value in variables.items():
            variables_string += f'{key}="{value}"\n'

        return variables_string
