import json
from pathlib import Path
from typing import Self

from alpaca.common.logging import logger
from alpaca.common.version import Version


class RecipeInfo:
    """
    A class to represent processed header description values for a recipe.
    """

    def __init__(self, path: Path | None, **kwargs):
        self.path: Path | None = path
        self.name: str | None = kwargs.get('name', None)
        self.version: Version | None = kwargs.get('version', None)
        self.release: str | None = kwargs.get('release', None)
        self.url: str | None = kwargs.get('url', None)
        self.licenses: list[str] = kwargs.get('licenses', [])
        self.dependencies: list[str] = kwargs.get('dependencies', [])
        self.build_dependencies: list[str] = kwargs.get('build_dependencies', [])
        self.sources: list[str] = kwargs.get('sources', [])
        self.sha256sums: list[str] = kwargs.get('sha256sums', [])

        if len(self.sources) != len(self.sha256sums):
            raise ValueError(
                f"Number of sources ({len(self.sources)}) does not match number of sha256sums ({len(self.sha256sums)})")

    @property
    def recipe_info_directory(self) -> Path:
        """
        Get the path where the recipe info is located
        """
        return Path(self.path).parent

    def write_json(self, path: Path | str):
        """
        Write recipe_info to a json file.

        Args:
            path (Path | str): The path where the recipe_info will be written.
        """
        path = Path(path).expanduser().resolve()

        logger.debug(f"Writing package description to {path}")

        info = {
            'name': self.name,
            'version': str(self.version) if self.version else None,
            'release': self.release,
            'url': self.url,
            'licenses': self.licenses,
            'dependencies': self.dependencies,
            'build_dependencies': self.build_dependencies,
            'sources': self.sources,
            'sha256sums': self.sha256sums
        }

        with open(path, 'w') as file:
            json.dump(info, file, indent=4)

        logger.debug(f"Package description written to {path}")

    def get_environment_variables(self) -> dict[str, str]:
        """
        Get the environment variables for the recipe info.

        Returns:
            dict[str, str]: A dictionary of environment variables.
        """
        return {
            "name": self.name,
            "version": str(self.version),
            "release": self.release
        }

    @classmethod
    def read_json_str(cls, json_str: str) -> Self:
        """
        Read a recipe info from a json string.

        Args:
            json_str (str): The json string containing the recipe info.

        Returns:
            RecipeInfo: An instance of RecipeInfo with the parsed data.
        """
        data = json.loads(json_str)

        return cls(
            path=None, # There is no path to set since we are reading from a tarball
            name=data.get('name'),
            version=Version(data.get('version')),
            release=data.get('release'),
            url=data.get('url'),
            licenses=data.get('licenses', []),
            dependencies=data.get('dependencies', []),
            build_dependencies=data.get('build_dependencies', []),
            sources=data.get('sources', []),
            sha256sums=data.get('sha256sums', [])
        )

    @classmethod
    def read_json(cls, path: Path | str) -> Self:
        """
        Read a recipe info from a json file.

        Args:
            path (Path | str): The path to the recipe info file.

        Returns:
            RecipeInfo: An instance of RecipeInfo with the parsed data.
        """
        path = Path(path)

        logger.debug(f"Reading package description from {path}")

        if not path.exists():
            raise FileNotFoundError(f"Recipe info file '{path}' does not exist.")

        with open(path, 'r') as file:
            json_str = file.read()

        recipe_info = cls.read_json_str(json_str)
        recipe_info.path = path

        return recipe_info
