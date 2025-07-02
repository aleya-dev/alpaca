from alpaca.recipes.version import Version


class RecipeDescription:
    """
    A class to represent a description for a package recipe.
    """

    def __init__(self, name: str, version: Version, release:str , url: str, licenses: list[str], dependencies: list[str],
            build_dependencies: list[str], sources: list[str], sha256sums: list[str], available_options: list[str]):
        self.name = name
        self.version = version
        self.release = release
        self.url = url
        self.licenses = licenses
        self.dependencies = dependencies
        self.build_dependencies = build_dependencies
        self.sources = sources
        self.sha256sums = sha256sums
        self.available_options = available_options

        if len(sources) != len(sha256sums):
            raise ValueError(
                f"Number of sources ({len(sources)}) does not match number of sha256sums ({len(sha256sums)})")
