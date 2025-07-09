from enum import Enum
from pathlib import Path
from typing import Self


class PackageServerType(Enum):
    """
    Enum representing the type of repository.
    """

    WEB = "web"
    LOCAL = "local"


class PackageServerRef:
    """
    A class representing a reference to a binary package repository, either an http(s) server or a local directory.

    The reference string should start with "web+" for web servers or "local+" for local directories.

    Attributes:
        path (str): The path to the repository. Read-only.
        type (PackageServerType): The type of the repository, either GIT or LOCAL. Read-only.
    """

    def __init__(self, ref_string: str):
        """
        Initialize a RepositoryRef object from a reference string.

        Args:
            ref_string (str): The reference string, which should start with "git+" or "local+".
        """

        if ref_string.startswith("web+"):
            self.path = ref_string[4:]
            self.type = PackageServerType.WEB
        elif ref_string.startswith("local+"):
            self.path = str(Path(ref_string[6:]).expanduser().resolve())
            self.type = PackageServerType.LOCAL
        else:
            raise ValueError(f"Invalid or unsupported repository type: {ref_string}")

    def __str__(self) -> str:
        """
        Get the string representation of the binary package reference
        """

        if self.type == PackageServerType.WEB:
            return f"web+{self.path}"
        elif self.type == PackageServerType.LOCAL:
            return f"local+{self.path}"
        else:
            raise ValueError(f"Invalid or unsupported binary package type: {self.type}")

    def __repr__(self) -> str:
        """
        Get the string representation of the binary package reference for debugging
        """

        return str(self)

    @classmethod
    def from_string(cls, string: str) -> list[Self] | None:
        """
        Create binary package references from a configuration string.
        Args:
            string (str): A comma-separated string of binary package references, e.g. web+
        Returns:
            list[Self] | None: A list of PackageServerRef objects or None if the string is empty.
        """

        if not string:
            return None

        repo_list = string.split(",")

        package_refs: list[PackageServerRef] = []
        for repo in repo_list:
            package_refs.append(PackageServerRef(repo))

        return package_refs
