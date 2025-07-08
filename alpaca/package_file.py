from tarfile import TarFile, open as tarfile_open
from pathlib import Path
from typing import Self

from alpaca.package_file_info import FileInfo, read_file_info_from_string
from alpaca.recipe_info import RecipeInfo


class PackageFile:
    def __init__(self, package_path: str | Path | None = None):
        self.package_path = package_path
        self._tar: TarFile | None = None

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if self._tar:
            self._tar.close()
            self._tar = None

    def _open(self):
        self._tar = tarfile_open(self.package_path, "r:gz")

    def read_recipe_info(self) -> RecipeInfo:
        """
        Read the recipe info from the package file.

        Returns:
            str: The contents of the recipe info file.
        """

        if not self._tar:
            self._open()

        try:
            with self._tar.extractfile(".recipe_info") as file:
                return RecipeInfo.read_json_str(file.read().decode("utf-8"))
        except KeyError:
            raise FileNotFoundError("Recipe info file not found in the package.")

