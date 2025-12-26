import tempfile
from os import rename, remove, chmod
from os.path import lexists, dirname
from pathlib import Path
from shutil import rmtree, copy2

from alpaca.core.common.confirmation import ask_user_confirmation
from alpaca.core.common.logging import get_logger
from alpaca.core.package_file_info import get_total_bytes, read_file_info_from_string
from alpaca.core.package import Package
from alpaca.core.recipe_info import RecipeInfo

logger = get_logger(__name__)


def _bytes_to_human(num):
    for unit in ("", "Ki", "Mi", "Gi"):

        if abs(num) < 1024.0:
            return f"{num:3.1f}{unit}B"

        num /= 1024.0

    return f"{num:.1f}TiB"


def _atomic_replace(src, dst):
    dst_dir = dirname(dst)

    with tempfile.NamedTemporaryFile(dir=dst_dir, delete=False) as tmp:
        copy2(src, tmp.name)
        tmp_name = tmp.name

    rename(tmp_name, dst)


class PackageRegistry:
    def __init__(self, prefix: Path | str = Path("/")):
        self.prefix = Path(prefix).resolve().expanduser()
        self.prefix.mkdir(parents=True, exist_ok=True)

        logger.debug(f"Using prefix: {self.prefix}")

    @property
    def registry_path(self) -> Path:
        return self.prefix / "var/lib/alpaca/packages"

    def ensure_directories(self):
        self.registry_path.mkdir(parents=True, exist_ok=True)

    def get_installed_packages(self) -> list[RecipeInfo]:
        if not self.registry_path.exists():
            raise FileNotFoundError(f"Package registry path {self.registry_path} does not exist")

        package_dirs = [p.name for p in self.registry_path.iterdir() if p.is_dir()]
        package_dirs.sort()

        packages: list[RecipeInfo] = []

        for package in package_dirs:
            package_dir = self.registry_path / package
            recipe_info_file = package_dir / ".recipe_info"

            if not recipe_info_file.exists():
                continue

            packages.append(RecipeInfo.read_from_recipe_info(recipe_info_file))

        return packages

    def check_dependencies_satisfied(self, info: RecipeInfo) -> bool:
        installed_packages = self.get_installed_packages()
        installed_package_names = {pkg.name for pkg in installed_packages}

        for dependency in info.dependencies:
            if dependency not in installed_package_names:
                logger.error(f"Dependency {dependency} for package {info.name} is not satisfied.")

        return True

    def get_installed_recipe_info_by_package_name(self, package_name: str) -> RecipeInfo | None:
        package_dir = self.registry_path / package_name

        if not package_dir.exists() and package_dir.is_dir():
            return None

        recipe_info_file = package_dir / ".recipe_info"

        if not recipe_info_file.exists():
            return None

        return RecipeInfo.read_from_recipe_info(recipe_info_file)

    def install(self, package: Package, ask_confirmation: bool = True):
        recipe_info = package.read_recipe_info()

        target_dir = self.registry_path / recipe_info.name
        target_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Installing package {recipe_info.name} to {target_dir}...")

        if not self.check_dependencies_satisfied(recipe_info):
            logger.error(f"Cannot install package {recipe_info.name} due to unsatisfied dependencies.")
            return

        state = self.get_installed_recipe_info_by_package_name(recipe_info.name)
        updating = True if state else False

        if state and state.version == recipe_info.version:
            logger.info(f"- Overwriting {recipe_info.name} ({recipe_info.version})")
        elif updating:
            logger.info(f"- Updating {recipe_info.name} ({state.version} => {recipe_info.version})")
        else:
            logger.info(f"- Installing {recipe_info.name} ({recipe_info.version})")

        file_info = package.read_file_info()
        logger.info(f"Total install size: {_bytes_to_human(get_total_bytes(file_info))}")
        logger.info("")

        if ask_confirmation and not ask_user_confirmation("Install package?", default=False):
            logger.info("Installation cancelled by user.")
            return

        with tempfile.TemporaryDirectory() as tempdir:
            package_file_tempdir = Path(tempdir)
            package.extract(package_file_tempdir)

            database_path = self.registry_path / recipe_info.name

            if not database_path.exists():
                logger.verbose(f"Creating database directory: {database_path}")
                database_path.mkdir(parents=True, exist_ok=True)

            for meta_file in [".recipe", ".file_info", ".recipe_info"]:
                src = package_file_tempdir / meta_file
                dst = database_path / meta_file
                logger.verbose(f"Moving metadata: {src} -> {dst}")
                _atomic_replace(src, dst)

            for source_file in package_file_tempdir.rglob("*"):
                if source_file.is_dir():
                    continue

                if source_file.name in [".recipe", ".file_info", ".recipe_info"]:
                    continue

                relative_path = source_file.relative_to(package_file_tempdir)
                destination_file = self.prefix / relative_path
                destination_parent = destination_file.parent

                if not destination_parent.exists():
                    logger.verbose(f"Creating directory: {destination_parent}")
                    destination_parent.mkdir(parents=True, exist_ok=True)

                if source_file.is_symlink():
                    symlink_target = source_file.readlink()

                    overwrite = False
                    if lexists(destination_file):
                        overwrite = True
                        destination_file.unlink()

                    logger.verbose(
                        f"{destination_file} -> {symlink_target} "
                        f"({"overwriting" if overwrite else "creating symlink"})")
                    destination_file.symlink_to(symlink_target)
                else:
                    mode = source_file.stat().st_mode

                    overwrite = False
                    if destination_file.exists():
                        overwrite = True
                        remove(destination_file)

                    logger.verbose(f"{"overwriting" if overwrite else "copying"} {relative_path} -> {destination_file}")
                    _atomic_replace(source_file, destination_file)
                    chmod(destination_file, mode & 0o777)

            logger.verbose(f"Removing temporary directory: {package_file_tempdir}")
            rmtree(package_file_tempdir, ignore_errors=True)

            logger.info(f"Package {recipe_info.name} ({recipe_info.version}) installed successfully.")

    def uninstall(self, name: str, ask_confirmation: bool = True):
        state = self.get_installed_recipe_info_by_package_name(name)

        if not state:
            logger.error(f"Package {name} is not installed.")
            return

        logger.info(f"Uninstalling package {state.name} ({state.version}-{state.build})...")

        file_info_path = self.registry_path / name / ".file_info"

        with open(file_info_path, "r") as file:
            file_info = read_file_info_from_string(file.read())

        logger.info(f"Total uninstall size: {_bytes_to_human(get_total_bytes(file_info))}")
        logger.info("")

        if ask_confirmation and not ask_user_confirmation(f"Uninstall package {state.name} ({state.version}-{state.build})?", default=False):
            logger.info("Uninstallation cancelled by user.")
            return

        for file in file_info:
            logger.verbose(f"Processing file: {file.name}")
            destination_file = self.prefix / file.name.lstrip("/")

            if not destination_file.exists() and not destination_file.is_symlink():
                logger.warning(f"File {destination_file} does not exist, skipping...")
                continue

            logger.verbose(f"Removing file: {destination_file}")
            if destination_file.is_symlink() or destination_file.is_file():
                destination_file.unlink()
            elif destination_file.is_dir():
                rmtree(destination_file, ignore_errors=True)

        rmtree(self.registry_path / name, ignore_errors=True)
        logger.info(f"Package {name} ({state.version}-{state.build}) uninstalled successfully.")
