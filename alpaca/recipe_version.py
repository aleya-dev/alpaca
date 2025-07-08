from typing import Self
from alpaca.common.version import Version


class RecipeVersion:
    """
    Represents a version of a recipe, including its version and release number.
    """

    def __init__(self, version: Version, release: int):
        """
        Initialize a RecipeVersion object.

        Args:
            version (Version): The version of the recipe.
            release (int): The release number of the recipe.
        """
        self.version = version
        self.release = release

    def __eq__(self, other):
        if not isinstance(other, RecipeVersion):
            return NotImplemented

        return self.version == other.version and self.release == other.release

    def __lt__(self, other):
        if not isinstance(other, RecipeVersion):
            return NotImplemented

        if self.version == other.version:
            return self.release < other.release

        return self.version < other.version

    def __str__(self):
        return f"{self.version.original}-{self.release}"

    @classmethod
    def from_string(cls, version_str: str) -> Self:
        """
        Create a RecipeVersion object from a version string.

        Args:
            version_str (str): The version string in the format 'version-release'.

        Returns:
            RecipeVersion: The created RecipeVersion object.
        """
        parts = version_str.split('-')

        if len(parts) > 2:
            raise ValueError("Invalid version string format. Expected format: 'version' or 'version-release'.")

        version = Version(parts[0])
        release = int(parts[1]) if len(parts) == 2 else 1

        return cls(version, release)

    @classmethod
    def find_closest_version_or_none(cls, versions: list[Self], requested_version: str | None) -> Self | None:
        """
        Find the closest version to the requested version.
        If no version is requested, returns the latest version.
        If no versions are available, returns None.
        Args:
            versions (list[Self]): List of RecipeVersion objects to search.
            requested_version (str | None): The requested version string.

        Returns:
            Self | None: The closest RecipeVersion object or None if no versions are available.
        """

        if not versions:
            return None

        if requested_version is None:
            return max(versions)

        requested_version_obj = cls.from_string(requested_version)

        # sort versions to ensure we can find the highest version
        versions.sort()

        highest_version = None

        # Ensure we always use the highest release for the requested version
        # TODO: Should it be allowed to specify a specific build version?
        for version in versions:
            if version == requested_version_obj:
                highest_version = version

        return highest_version
