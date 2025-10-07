def decompose_package_atom_from_name(name: str) -> tuple[str, str | None]:
    """
    Decompose a package name into its base name and version.

    Args:
        name (str): The package name in the format <name> or <name>/<version>.

    Returns:
        tuple[str, str | None]: A tuple containing the base name and the version (if specified).
    """
    parts = name.split('/')
    if len(parts) > 2:
        raise ValueError("Invalid package name format. Expected format: <name> or <name>/<version>")

    base_name = parts[0]
    version = parts[1] if len(parts) == 2 else None

    return base_name, version