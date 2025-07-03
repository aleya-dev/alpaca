import json
from os.path import join
from pathlib import Path
from shlex import split
from typing import Self

from alpaca.common.logging import logger
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

    def write_package_description(self, path: Path | str):
        """
        Write the recipe description to a package description file.

        Args:
            path (Path | str): The path where the package description will be written.
        """
        path = Path(path).expanduser().resolve()

        logger.debug(f"Writing package description to {path}")

        with open(path, 'w') as file:
            file.write(f'name = "{self.name}"\n')
            file.write(f'version = "{self.version}"\n')
            file.write(f'release = "{self.release}"\n')
            file.write(f'url = "{self.url}"\n')
            file.write(f"licenses = ({(' '.join(f'"{license}"' for license in self.licenses))})\n")
            file.write(f"dependencies = ({(' '.join(f'"{dep}"' for dep in self.dependencies))})\n")
            file.write(f"build_dependencies = ({(' '.join(f'"{dep}"' for dep in self.build_dependencies))})\n")
            file.write(f"sources = ({(' '.join(f'"{src}"' for src in self.sources))})\n")
            file.write(f"sha256sums = ({(' '.join(f'"{sum}"' for sum in self.sha256sums))})\n")
            file.write(f"package_options = ({(' '.join(f'"{opt}"' for opt in self.available_options))})\n")

        logger.debug(f"Package description written to {path}")

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

    @classmethod
    def load_from_workspace_path(cls, workspace_path: Path | str) -> Self:
        """
        Load a recipe description from build_context.json in the specified workspace path.

        Args:
            workspace_path (Path | str): The path to build workspace or build context.

        Returns:
            RecipeDescription: An instance of RecipeDescription.
        """

        workspace_path = Path(workspace_path).expanduser().resolve()
        build_context_path = join(workspace_path, "build_context.json")

        with open(build_context_path, 'r') as file:
            build_context = json.load(file)

            return cls(
                name=build_context["name"],
                version=Version(build_context["version"]),
                release=build_context["release"],
                url=build_context["url"],
                licenses=build_context["licenses"],
                dependencies=build_context["dependencies"],
                build_dependencies=build_context["build_dependencies"],
                sources=build_context["sources"],
                sha256sums=build_context["sha256sums"],
                available_options=build_context["available_options"]
            )
