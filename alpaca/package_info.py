import json
from pathlib import Path
from typing import Self

from alpaca.common.logging import logger
from alpaca.common.version import Version
from alpaca.package_dependency import PackageDependency, PackageDependencyType


class PackageInfo:
    """
    A class to represent processed header description values for a package.
    """

    def __init__(self, path: Path | None, **kwargs):
        self.path: Path | None = path
        self.name: str | None = kwargs.get('name', None)
        self.stream: str | None = kwargs.get('stream', None)
        self.version: Version | None = kwargs.get('version', None)
        self.release: str | None = kwargs.get('release', None)
        self.url: str | None = kwargs.get('url', None)
        self.licenses: list[str] = kwargs.get('licenses', [])
        self.dependencies: list[PackageDependency] = kwargs.get('dependencies', [])
        self.build_dependencies: list[PackageDependency] = kwargs.get('build_dependencies', [])

    @property
    def package_info_directory(self) -> Path:
        """
        Get the path where the package info is located
        """
        return Path(self.path).parent

    @property
    def package_dependency(self) -> PackageDependency:
        """
        Get the package dependency representation of this package info.

        Returns:
            PackageDependency: A PackageDependency object representing this package.
        """
        return PackageDependency(
            package_type=PackageDependencyType.RUNTIME,
            atom=f"{self.atom}",
            dependencies=self.dependencies
        )

    def write_json(self, path: Path | str):
        """
        Write package_info to a json file.

        Args:
            path (Path | str): The path where the package_info will be written.
        """
        path = Path(path).expanduser().resolve()

        logger.debug(f"Writing package description to {path}")

        info = {
            'name': self.name,
            'stream': self.stream,
            'version': str(self.version) if self.version else None,
            'release': self.release,
            'url': self.url,
            'licenses': self.licenses,
            'dependencies': [dep.to_dict() for dep in self.dependencies],
            'build_dependencies': [dep.to_dict() for dep in self.build_dependencies]
        }

        with open(path, 'w') as file:
            json.dump(info, file, indent=4)

        logger.debug(f"Package description written to {path}")

    def get_environment_variables(self) -> dict[str, str]:
        """
        Get the environment variables for the package info.

        Returns:
            dict[str, str]: A dictionary of environment variables.
        """
        return {
            "name": self.name,
            "version": str(self.version),
            "release": self.release,
            "stream": self.stream
        }

    @property
    def file_atom(self):
        return f"{self.name}-{self.version}-{self.release}"

    @property
    def atom(self):
        return f"{self.name}/{self.version}-{self.release}"

    @classmethod
    def read_json_str(cls, json_str: str) -> Self:
        """
        Read a package info from a json string.

        Args:
            json_str (str): The json string containing the package info.

        Returns:
            PackageInfo: An instance of RecipeInfo with the parsed data.
        """
        data = json.loads(json_str)

        return cls(
            path=None,  # There is no path to set since we are reading from a tarball
            name=data.get('name'),
            stream=data.get('stream'),
            version=Version(data.get('version')),
            release=data.get('release'),
            url=data.get('url'),
            licenses=data.get('licenses', []),
            dependencies=[PackageDependency.from_dict(dep) for dep in data.get('dependencies', [])],
            build_dependencies=[PackageDependency.from_dict(dep) for dep in data.get('build_dependencies', [])],
            sources=data.get('sources', []),
            sha256sums=data.get('sha256sums', [])
        )

    @classmethod
    def read_json(cls, path: Path | str) -> Self:
        """
        Read a package info from a json file.

        Args:
            path (Path | str): The path to the package info file.

        Returns:
            PackageInfo: An instance of RecipeInfo with the parsed data.
        """
        path = Path(path)

        logger.debug(f"Reading package description from {path}")

        if not path.exists():
            raise FileNotFoundError(f"package info file '{path}' does not exist.")

        with open(path, 'r') as file:
            json_str = file.read()

        package_info = cls.read_json_str(json_str)
        package_info.path = path

        return package_info
