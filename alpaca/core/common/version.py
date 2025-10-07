from functools import total_ordering


@total_ordering
class Version:
    """
    A version class that supports:
      - Unlimited dot-separated numeric segments (e.g., '1.2.3.4.5')
      - Alphabetical comparison if the version contains no dots (e.g., 'alpha', 'beta')

    Versions with dots are parsed as tuples of integers and compared numerically.
    Versions without dots are compared as plain strings (alphabetically).

    A numeric version is always considered less than an alphabetical version.
    """

    def __init__(self, version: str):
        """
        Initializes a Version instance.

        Args:
            version (str): The version string to parse and store.
        """
        self.original = version

        if '.' in version:
            self.parts = tuple(int(part) for part in version.split('.'))
            self.is_numeric = True
        else:
            self.parts = version
            self.is_numeric = False

    def __eq__(self, other):
        """
        Checks for equality between two Version instances.

        Args:
            other (Version): Another version to compare with.

        Returns:
            bool: True if the versions are equal, False otherwise.
        """
        if not isinstance(other, Version):
            return NotImplemented

        return self.parts == other.parts and self.is_numeric == other.is_numeric

    def __lt__(self, other):
        """
        Checks if this version is less than another Version instance.

        Args:
            other (Version): Another version to compare with.

        Returns:
            bool: True if this version is less than the other, False otherwise.
        """
        if not isinstance(other, Version):
            return NotImplemented

        if self.is_numeric and other.is_numeric:
            return self.parts < other.parts
        elif not self.is_numeric and not other.is_numeric:
            return self.parts < other.parts  # alphabetic comparison
        else:
            return self.is_numeric  # numeric < alphabetic

    def __hash__(self):
        """
        Computes a hash for the version, making it usable in sets and as dict keys.

        Returns:
            int: Hash value for the version.
        """
        return hash((self.parts, self.is_numeric))

    def __repr__(self):
        """
        Returns the developer-friendly string representation.

        Returns:
            str: Representation of the version object.
        """
        return f"Version('{self.original}')"

    def __str__(self):
        """
        Returns the user-friendly string representation of the version.
        """
        return self.original
