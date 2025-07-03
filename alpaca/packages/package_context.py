import tarfile
from typing import Self

from alpaca.packages.package_file_info import FileInfo, read_file_info_from_string
from alpaca.recipes.recipe_description import RecipeDescription


class PackageContext:
    def __init__(self, package_path: str):
        self.package_path = package_path
        self._tar = None
        self.description = None
        self.file_info = [FileInfo]
        self.hash = None

    def __enter__(self) -> Self:
        self._tar = tarfile.open(self.package_path, "r:gz")

        if ".package_info" not in self._tar.getnames():
            raise ValueError(f"The package '{self.package_path}' does not contain a valid .package_info file.")

        self.description = RecipeDescription.read_from_package_description_string(
            self._tar.extractfile(".package_info").read().decode('utf-8'))

        self.file_info = read_file_info_from_string(
            self._tar.extractfile(".file_info").read().decode('utf-8')
        )

        self.hash = self._tar.extractfile(".hash").read().decode('utf-8').strip()

        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if self._tar:
            self._tar.close()
            self._tar = None
