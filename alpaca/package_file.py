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

    def read_file_info(self) -> list[FileInfo]:
        """
        Read the file info from the package file.

        Returns:
            list[FileInfo]: A list of FileInfo objects containing information about the files in the package.
        """

        if not self._tar:
            self._open()

        try:
            with self._tar.extractfile(".file_info") as file:
                file_info_string = file.read().decode("utf-8")
                return read_file_info_from_string(file_info_string)
        except KeyError:
            raise FileNotFoundError("File info file not found in the package.")

    def extract_file(self, file: str, destination: str | Path):
        """
        Extract a specific file from the package to the destination.

        Args:
            file (str): The name of the file to extract.
            destination (str | Path): The path where the file should be extracted.
        """

        if not self._tar:
            self._open()

        try:
            self._tar.extract(file, path=destination)
        except KeyError:
            raise FileNotFoundError(f"File '{file}' not found in the package.")

    def extract(self, destination: str | Path):
        """
        Extract all files from the package to the destination except for the package database files.
        """

        if not self._tar:
            self._open()

        for member in self._tar.getmembers():
            if member.name not in (".recipe", ".file_info", ".recipe_info"):
                self._tar.extract(member, path=destination)
            else:
                continue
