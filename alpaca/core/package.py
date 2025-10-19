from tarfile import TarFile, open as tarfile_open
from pathlib import Path
from typing import Self

from alpaca.core.common.logging import get_logger
from alpaca.core.common.package_file_info import FileInfo, read_file_info_from_string
from alpaca.core.recipe_info import RecipeInfo

logger = get_logger(__name__)


class Package:
    def __init__(self, path: Path):
        self.path = path
        self._recipe_info: RecipeInfo | None = None
        self._tar: TarFile | None = None

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if self._tar:
            self._tar.close()
            self._tar = None

    def _open(self):
        self._tar = tarfile_open(self.path, "r:xz")

    def read_recipe_info(self) -> RecipeInfo:
        """
        Read the recipe info from the package file.

        Returns:
            RecipeInfo: The RecipeInfo object containing information about the package.
        """

        if self._recipe_info:
            return self._recipe_info

        if not self._tar:
            self._open()

        try:
            recipe_info_file = self._tar.getmember(".recipe_info")
            with self._tar.extractfile(recipe_info_file) as recipe_info_f:
                self._recipe_info = RecipeInfo.read_from_json_string(recipe_info_f.read().decode("utf-8"))
        except KeyError:
            raise FileNotFoundError("Recipe info file not found in the package.")

        return self._recipe_info

    def read_file_info(self) -> list[FileInfo]:
        """
        Read the file info from the package file.

        Returns:
            list[FileInfo]: A list of FileInfo objects containing information about the files in the package.
        """

        try:
            with self._tar.extractfile(".file_info") as file:
                return read_file_info_from_string(file.read().decode("utf-8"))
        except KeyError:
            raise FileNotFoundError("File info file not found in the package.")

    def extract(self, destination: str | Path):
        """
        Extract all files from the package to the destination directory.
        """
        self._tar.extractall(path=destination)
