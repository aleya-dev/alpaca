from enum import Enum
from typing import Self, List, Set

from alpaca.atom import decompose_package_atom_from_name


class PackageDependencyType(Enum):
    RUNTIME = "runtime"
    BUILD = "build"


class PackageDependency:
    def __init__(self, package_type: PackageDependencyType, atom: str, dependencies: list[Self] = None):
        self.type = package_type
        self.atom = atom
        self.dependencies = dependencies if dependencies is not None else []

        self.name, self.version = decompose_package_atom_from_name(atom)

    def __eq__(self, other: Self) -> bool:
        return self.atom == other.atom

    def __lt__(self, other: Self) -> bool:
        return self.atom < other.atom

    def to_dict(self) -> dict:
        return {
            'type': self.type.value,
            'version': self.atom,
            'dependencies': [dep.to_dict() for dep in self.dependencies]
        }

    def get_installation_order(self, include_self: bool = True) -> List[Self]:
        visited_atoms: Set[str] = set()
        result: List[Self] = []

        def visit(pkg: Self):
            if pkg.atom in visited_atoms:
                return

            visited_atoms.add(pkg.atom)

            for dep in pkg.dependencies:
                visit(dep)

            result.append(pkg)

        visit(self)

        if not include_self:
            result = [pkg for pkg in result if pkg.atom != self.atom]

        return result

    @classmethod
    def from_dict(cls, data: dict) -> Self:
        package_type = PackageDependencyType(data['type'])
        atom = data['version']
        dependencies = [cls.from_dict(dep) for dep in data.get('dependencies', [])]

        instance = cls(package_type, atom)
        instance.dependencies = dependencies
        return instance
