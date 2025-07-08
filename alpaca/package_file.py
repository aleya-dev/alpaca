from tarfile import TarFile, open as tarfile_open
from pathlib import Path
from typing import Self


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
