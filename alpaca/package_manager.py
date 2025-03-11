from alpaca.package import Package
from alpaca.package_description import Atom
from alpaca.configuration import Configuration
from alpaca.logging import logger
from collections import deque, defaultdict
import os


_LATEST_VERSION_IDENTIFIER = "latest"


class PackageManager:
    def __init__(self):
        self.packages: dict[str, Package] = {}

    def install_package(self, package_atom: str):
        package_install_list = self._resolve_package_list(package_atom)

        for package in package_install_list:
            package.build()

    def _resolve_package_list(self, package_atom: str) -> list[Package]:
        self.packages: dict[str, Package] = {}

        requested_package = self._resolve_package(package_atom)

        graph = defaultdict(list)
        in_degree = {}

        for package in self.packages.values():
            in_degree[package] = 0

        for package in self.packages.values():
            logger.verbose(f"Processing package {package.description.atom.name}")
            logger.verbose(f"  Dependencies: {package.description.dependencies}")

            for dependency in package.description.dependencies:
                logger.verbose(
                    f"Adding dependency {dependency} for package {package.description.atom.name}"
                )
                graph[dependency].append(package)
                in_degree[package] += 1

        queue = deque([pkg for pkg in self.packages.values() if in_degree[pkg] == 0])
        sorted_order = []

        while queue:
            current = queue.popleft()
            sorted_order.append(current)

            for package in graph[current]:
                in_degree[package] -= 1
                if in_degree[package] == 0:
                    queue.append(package)

        # When a package has no dependencies, it is already in this list. Needs investigation
        if len(sorted_order) != len(self.packages):
            sorted_order.append(requested_package)

        if len(sorted_order) != len(self.packages):
            raise ValueError("Cycle detected in package dependencies")

        return sorted_order

    def _resolve_package(
        self, package_atom: str, throw_on_failure: bool = True
    ) -> Package:
        atom = self._resolve_package_atom_info(package_atom)

        package: Package | None = None

        if atom in self.packages:
            logger.verbose(f"Package {atom} loaded from cache")
            package = self.packages[atom]
        else:
            logger.verbose(f"Searching for package {atom} in repositories...")

            config = Configuration()
            for repo in config.repositories:
                logger.verbose(f"Searching for package {atom} in {repo.get_name()}")

                for stream in config.package_streams:
                    recipe_base_path = os.path.join(repo.get_path(), stream, atom.name)
                    recipe_path = os.path.join(
                        recipe_base_path, f"{atom.name}-{atom.version}.sh"
                    )
                    recipe_path2 = os.path.join(
                        recipe_base_path,
                        f"{atom.name}-{atom.version}-{atom.release}.sh",
                    )

                    if os.path.exists(recipe_path):
                        logger.verbose(
                            f"Found package {atom} in repo {repo.get_name()}"
                        )

                        package = Package(atom, recipe_path)
                        self._add_package_to_cache(atom, package)
                        break
                    elif os.path.exists(recipe_path2):
                        logger.verbose(f"Found package {atom} in {repo.get_name()}")

                        package = Package(atom, recipe_path2)
                        self._add_package_to_cache(atom, package)
                        break

            if package is None and throw_on_failure:
                raise ValueError(f"Package {package_atom} not found in any repository")

            self._resolve_package_dependencies(package)

            return package

    def _resolve_package_dependencies(self, package: Package):
        dependency_count = len(package.description.dependencies)

        if dependency_count == 0:
            return

        logger.info(
            f"Resolving {dependency_count} dependencies for package {package.description.atom.name}"
        )

        for dependency in package.description.dependencies:
            self._resolve_package(dependency)

    def _resolve_package_atom_info(self, atom_string: str) -> Atom:
        if "/" in atom_string:
            split_result = atom_string.split("/")

            if len(split_result) != 2:
                raise ValueError(f"Invalid package: {atom_string}")

            if split_result[0] == "" or split_result[1] == "":
                raise ValueError(f"Invalid package: {atom_string}")

            name = split_result[0]
            version = split_result[1]
        else:
            name = atom_string
            version = _LATEST_VERSION_IDENTIFIER

        if version == _LATEST_VERSION_IDENTIFIER:
            version = self._find_latest_package_version(name)

        (version, release) = self._parse_version_release_number(version)
        return Atom(name, version, release)

    def _parse_version_release_number(self, version: str) -> tuple[str, str]:
        version_split = version.split("-")

        if len(version_split) > 2:
            raise ValueError(f"Invalid version: {version}")

        if len(version_split) == 1:
            return version, "0"
        else:
            return version_split[0], version_split[1]

    def _add_package_to_cache(self, version: Atom, package: Package):
        self.packages[version] = package
        logger.verbose(f"Package {version} added to cache")

    def _find_latest_package_version(self, package_name: str) -> str:
        logger.info(f"Resolving latest version for package {package_name}")

        config = Configuration()

        for repo in config.repositories:
            logger.verbose(f"Searching for package {package_name} in {repo.get_name()}")

            for stream in config.package_streams:
                latest_info_path = os.path.join(
                    repo.get_path(), stream, package_name, _LATEST_VERSION_IDENTIFIER
                )

                if os.path.exists(latest_info_path):
                    with open(latest_info_path, "r") as f:
                        result = f.read().strip()
                        logger.info(
                            f"Latest version for package {package_name} is {result}"
                        )
                        return result

        raise ValueError(f"No package found for {package_name}")
