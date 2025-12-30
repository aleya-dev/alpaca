from dataclasses import dataclass
from importlib import resources
from os.path import dirname
from pathlib import Path
from typing import List, Union
import json

from alpaca.core.common.shell_command import ShellCommand

ARRAY_KEYS = {"licenses", "dependencies", "build_dependencies", "provides", "sources", "sha256sums", }


def parse_line(line: str) -> tuple[str, str]:
    """Parse a key=value line, stripping quotes and whitespace."""
    key, value = line.split("=", 1)
    return key.strip(), value.strip().strip('"').strip("'")


def read_recipe_header(file_path: Path) -> dict[str, Union[str, List[str]]]:
    """Execute the Bash script to read recipe header and return info as a dict."""
    template_text = resources.read_text("alpaca.core.scripts", "read_recipe_header.sh")
    result = ShellCommand.exec([template_text, "_", file_path], print_output=False, throw_on_error=True)

    info = {}
    current_key = None
    current_array = []

    for line in result.stdout.split("\0"):

        if "=" in line:
            key, value = parse_line(line)

            if key.endswith("[]"):
                key = key[:-2]

                if current_key != key:
                    if current_key is not None:
                        info[current_key] = current_array

                    current_key = key
                    current_array = [value]

                else:
                    current_array.append(value)
            else:
                if current_key is not None:
                    info[current_key] = current_array
                    current_key = None
                    current_array = []

                info[key] = value

    if current_key is not None:
        info[current_key] = current_array

    return info


@dataclass
class RecipeInfo:
    """Class for keeping track of recipe information.

    Attributes:
        path (str): The file path to the recipe.
        name (str): The name of the recipe.
        stream (str): The stream name.
        version (str): The recipe version.
        build (int): The build number.
        licenses (List[str]): List of license strings.
        dependencies (List[str]): List of runtime dependencies.
        build_dependencies (List[str]): List of build-time dependencies.
        provides (List[str]): List of features provided by the recipe.
        sources (List[str]): List of source files or URLs.
        sha256sums (List[str]): List of SHA256 checksums for sources.
        url (str): Homepage or reference URL for the recipe.
    """

    path: Path
    name: str
    stream: str
    version: str
    build: int
    licenses: List[str]
    dependencies: List[str]
    build_dependencies: List[str]
    provides: List[str]
    sources: List[str]
    sha256sums: List[str]
    url: str = ""

    @property
    def recipe_directory(self) -> Path:
        """Get the directory of the recipe file."""
        return Path(dirname(self.path))

    @staticmethod
    def parse_from_recipe(file_path: Path) -> "RecipeInfo":
        """Load recipe information from a file using the Bash script."""
        info = read_recipe_header(file_path)

        return RecipeInfo(
            path=file_path,
            name=info.get("name"),
            stream=info.get("stream"),
            version=info.get("version"),
            build=int(info.get("build")),
            licenses=info.get("licenses"),
            dependencies=info.get("dependencies"),
            build_dependencies=info.get("build_dependencies"),
            provides=info.get("provides"),
            sources=info.get("sources"),
            sha256sums=info.get("sha256sums"),
            url=info.get("url")
        )

    @staticmethod
    def read_from_json_string(json_string: str) -> "RecipeInfo":
        """Read the RecipeInfo from a JSON string."""
        data = json.loads(json_string)

        return RecipeInfo(
            path=Path("#TAR#/.recipe"),  # Find a better way for this...
            name=data.get("name"),
            stream=data.get("stream"),
            version=data.get("version"),
            build=int(data.get("build")),
            licenses=data.get("licenses", []),
            dependencies=data.get("dependencies", []),
            build_dependencies=data.get("build_dependencies", []),
            provides=data.get("provides", []),
            sources=data.get("sources", []),
            sha256sums=data.get("sha256sums", []),
            url=data.get("url", "")
        )

    @staticmethod
    def read_from_recipe_info(path: Path) -> "RecipeInfo":
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        return RecipeInfo(
            path=path.parent / ".recipe",  # When loading from package dir, assume .recipe file
            name=data.get("name"),
            stream=data.get("stream"),
            version=data.get("version"),
            build=int(data.get("build")),
            licenses=data.get("licenses", []),
            dependencies=data.get("dependencies", []),
            build_dependencies=data.get("build_dependencies", []),
            provides=data.get("provides", []),
            sources=data.get("sources", []),
            sha256sums=data.get("sha256sums", []),
            url=data.get("url", "")
        )

    @staticmethod
    def read_from_package_dir(path: Path) -> "RecipeInfo":
        """Read the RecipeInfo from a JSON file."""

        recipe_info_json = path / ".recipe_info"
        return RecipeInfo.read_from_recipe_info(recipe_info_json)

    def is_valid(self) -> bool:
        """Check if the recipe information is valid."""
        if not all([self.path, self.name, self.stream, self.version]):
            return False

        if not self.licenses or not self.provides:
            return False

        if len(self.sources) != len(self.sha256sums):
            return False

        return True

    def write_to_file(self, file_path: Path):
        """Write the RecipeInfo to a JSON file."""
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=4)

    def to_dict(self) -> dict:
        """Convert the RecipeInfo to a dictionary."""
        return {
            "path": str(self.path),
            "name": self.name,
            "stream": self.stream,
            "version": self.version,
            "build": self.build,
            "licenses": self.licenses,
            "dependencies": self.dependencies,
            "build_dependencies": self.build_dependencies,
            "provides": self.provides,
            "sources": self.sources,
            "sha256sums": self.sha256sums,
            "url": self.url
        }

    def get_variables(self) -> dict[str, str]:
        return {
            "name": str(self.name),
            "stream": str(self.stream),
            "version": str(self.version),
            "build": str(self.build),
            "url": str(self.url)
        }
