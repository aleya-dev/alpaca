import hashlib
from enum import Enum
from os.path import join
from pathlib import Path
from typing import Self


class RepositoryType(Enum):
    """
    Enum representing the type of repository.
    """

    GIT = "git"
    LOCAL = "local"


class RepositoryRef:
    """
    A class representing a reference to a repository, either a Git repository or a local directory.

    The reference string should start with "git+" for Git repositories or "local+" for local directories.

    Attributes:
        path (str): The path to the repository. Read-only.
        type (RepositoryType): The type of the repository, either GIT or LOCAL. Read-only.
    """

    def __init__(self, ref_string: str):
        """
        Initialize a RepositoryRef object from a reference string.

        Args:
            ref_string (str): The reference string, which should start with "git+" or "local+".
        """

        if ref_string.startswith("git+"):
            self.path = ref_string[4:]
            self.type = RepositoryType.GIT
        elif ref_string.startswith("local+"):
            self.path = str(Path(ref_string[6:]).expanduser().resolve())
            self.type = RepositoryType.LOCAL
        else:
            raise ValueError(f"Invalid or unsupported repository type: {ref_string}")

    def get_hash(self):
        """
        Get a hash of the repository reference
        """

        hash_object = hashlib.sha256()
        hash_object.update(str(self).encode("utf-8"))
        return hash_object.hexdigest()

    def get_cache_path(self, cache_base_path: str) -> Path:
        """
        Get the cache path for the repository reference.
        """
        if self.type == RepositoryType.LOCAL:
            return Path(self.path)

        return Path(join(cache_base_path, self.get_hash()))

    def __str__(self) -> str:
        """
        Get the string representation of the repository reference
        """

        if self.type == RepositoryType.GIT:
            return f"git+{self.path}"
        elif self.type == RepositoryType.LOCAL:
            return f"local+{self.path}"
        else:
            raise ValueError(f"Invalid or unsupported repository type: {self.type}")

    def __repr__(self) -> str:
        """
        Get the string representation of the repository reference for debugging
        """

        return str(self)

    @classmethod
    def from_string(cls, string: str) -> list[Self] | None:
        """
        Create repository references from a configuration string.
        Args:
            string (str): A comma-separated string of repository references, e.g. git+
        Returns:
            list[Self] | None: A list of RepositoryRef objects or None if the string is empty.
        """

        if not string:
            return None

        repo_list = string.split(",")

        repositories: list[RepositoryRef] = []
        for repo in repo_list:
            repositories.append(RepositoryRef(repo))

        return repositories
