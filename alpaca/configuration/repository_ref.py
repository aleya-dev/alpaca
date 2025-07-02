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
    def __init__(self, ref_string: str):
        """
        Initialize a RepositoryRef object from a reference string.

        Args:
            ref_string (str): The reference string, which should start with "git+" or "local+".
        """

        if ref_string.startswith("git+"):
            self._path = ref_string[4:]
            self._repo_type = RepositoryType.GIT
        elif ref_string.startswith("local+"):
            self._path = str(Path(ref_string[6:]).expanduser().resolve())
            self._repo_type = RepositoryType.LOCAL
        else:
            raise ValueError(f"Invalid or unsupported repository type: {ref_string}")

    def get_path(self) -> str:
        """
        Get the path to the repository as defined in the repository entry

        Returns:
            str: The path to the repository as defined in the repository entry
        """

        return self._path

    def get_type(self) -> RepositoryType:
        """
        Get the type of the repository
        """

        return self._repo_type


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
        if self._repo_type == RepositoryType.LOCAL:
            return Path(self._path)

        return Path(join(cache_base_path, self.get_hash()))

    def __str__(self) -> str:
        """
        Get the string representation of the repository reference
        """

        if self._repo_type == RepositoryType.GIT:
            return f"git+{self._path}"
        elif self._repo_type == RepositoryType.LOCAL:
            return f"local+{self._path}"
        else:
            raise ValueError(f"Invalid or unsupported repository type: {self._repo_type}")

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
