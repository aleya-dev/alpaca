from shlex import split
from typing import Self

from alpaca.recipes.version import Version


def _parse_recipe_text_to_dict(text: str) -> dict[str, str]:
    result = {}

    for lineno, line in enumerate(text.splitlines(), start=1):
        line = line.strip()

        if not line or line.startswith('#'):
            continue

        if '=' not in line:
            raise ValueError(f"Invalid line {lineno}: '{line}'. Expected format 'key = value'.")

        key, value = line.split('=', 1)
        result[key.strip()] = value.strip()

    return result


def _parse_array(value: str) -> list[str]:
    if not (value.startswith('(') and value.endswith(')')):
        raise ValueError(f"Invalid array syntax: {value}")
    return split(value[1:-1])


class RecipeDescription:
    """
    A class to represent a description for a package recipe.
    """
    def __init__(self, **kwargs):
        self.name: str | None = kwargs.get('name', None)
        self.version: Version | None = kwargs.get('version', None)
        self.release: str | None = kwargs.get('release', None)
        self.url: str | None = kwargs.get('url', None)
        self.licenses: list[str] = kwargs.get('licenses', [])
        self.dependencies: list[str] = kwargs.get('dependencies', [])
        self.build_dependencies: list[str] = kwargs.get('build_dependencies', [])
        self.sources: list[str] = kwargs.get('sources', [])
        self.sha256sums: list[str] = kwargs.get('sha256sums', [])
        self.available_options: list[str] = kwargs.get('available_options', [])

        if len(self.sources) != len(self.sha256sums):
            raise ValueError(
                f"Number of sources ({len(self.sources)}) does not match number of sha256sums ({len(self.sha256sums)})")

    @classmethod
    def read_from_package_description_string(cls, package_string: str) -> Self:
        """
        Read a recipe description from a package description string.

        Args:
            package_string (str): The package description string.

        Returns:
            RecipeDescription: An instance of RecipeDescription.
        """

        data = _parse_recipe_text_to_dict(package_string)

        return cls(
            name=data["name"].strip('"'),
            version=Version(data["version"].strip('"')),
            release=data["release"].strip('"'),
            url=data["url"].strip('"'),
            licenses=_parse_array(data["licenses"]),
            dependencies=_parse_array(data["dependencies"]),
            build_dependencies=_parse_array(data["build_dependencies"]),
            sources=_parse_array(data["sources"]),
            sha256sums=_parse_array(data["sha256sums"]),
            available_options=_parse_array(data["package_options"]),
        )
