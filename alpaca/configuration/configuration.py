from argparse import Namespace
from configparser import ConfigParser
from os import environ, getcwd, access, X_OK
from os.path import exists, abspath, expandvars, expanduser, join
from pathlib import Path
from typing import Self

from alpaca.common.logging import logger
from alpaca.configuration.repository_ref import RepositoryRef

_system_config_path = "/etc/alpaca.conf"
_user_config_path = abspath(expandvars(expanduser("~/.alpaca")))
_alpaca_config_env_var = "ALPACA_CONFIG"

_default_fakeroot_executable = "/usr/bin/fakeroot"
_default_shell_executable = "/usr/bin/bash"
_default_cat_executable = "/usr/bin/cat"


_default_recipe_file_extension = ".recipe.sh"
_default_package_file_extension = ".alpaca-package.tgz"


class Configuration:
    """
    Configuration class for managing build settings and options.
    """

    def __init__(self, **kwargs) -> None:
        self.verbose_output: bool | None = kwargs.get('verbose_output', None)
        self.suppress_build_output: bool | None = kwargs.get('suppress_build_output', None)
        self.show_download_progress: bool | None = kwargs.get('show_download_progress', None)

        self.target_architecture: str | None = kwargs.get('target_architecture', None)

        self.c_flags: str | None = kwargs.get('c_flags', None)
        self.cpp_flags: str | None = kwargs.get('cpp_flags', None)
        self.ld_flags: str | None = kwargs.get('ld_flags', None)
        self.make_flags: str | None = kwargs.get('make_flags', None)
        self.ninja_flags: str | None = kwargs.get('ninja_flags', None)

        self.repositories: list[RepositoryRef] | None = kwargs.get('repositories', None)
        self.package_streams: list[str] | None = kwargs.get('package_streams', None)

        self.keep_build_directory: bool | None = kwargs.get('keep_build_directory', None)
        self.skip_package_check: bool | None = kwargs.get('skip_package_check', None)

        self.download_cache_path: str | None = kwargs.get('download_cache_path', None)
        self.force_download: str | None = kwargs.get('force_download', None)
        self.repository_cache_path: str | None = kwargs.get('repository_cache_path', None)

        self.package_workspace_path: str | None = kwargs.get('package_workspace_path', None)
        self.package_delete_workspace: bool | None = kwargs.get('package_delete_workspace', None)
        self.package_artifact_path: str | None = kwargs.get('package_artifact_path', None)

        self.prefix: str | None = kwargs.get('prefix', None)

        self.fakeroot_executable: str | None = kwargs.get('fakeroot_executable', None)
        self.shell_executable: str | None = kwargs.get('shell_executable', None)
        self.cat_executable: str | None = kwargs.get('cat_executable', None)

        self.recipe_file_extension: str | None = kwargs.get('recipe_file_extension', None)
        self.package_file_extension: str | None = kwargs.get('package_file_extension', None)

    @classmethod
    def create_application_config(cls, application_arguments: Namespace) -> Self:
        """
        Create a configuration instance for the application.

        This method merges configurations from system files, user files, environment variables,
        and command line arguments. The order of precedence is:

        1. System configuration file (e.g., /etc/alpaca.conf)
        2. User configuration file (e.g., ~/.alpaca)
        3. Environment variables (e.g., ALPACA_CONFIG)
        4. Command line arguments

        The last non-None value for each attribute will be used.

        Args:
            application_arguments (Namespace): Parsed command line arguments.

        Returns:
            Configuration: Merged configuration instance.
        """

        system_config = None

        config_env_var = environ.get(_alpaca_config_env_var, None)
        if config_env_var is not None:
            logger.debug(f"Using configuration file specified in {_alpaca_config_env_var} environment variable")

            aleya_config_env_path = config_env_var
            if exists(aleya_config_env_path):
                system_config = Configuration._create_from_config_file(aleya_config_env_path)
            else:
                logger.warning(f"Configuration file specified in {_alpaca_config_env_var} environment "
                               f" variable does not exist: {aleya_config_env_path}.")

        if system_config is None:
            logger.debug(f"Loading system config file: {_system_config_path}")
            system_config = Configuration._create_from_config_file(_system_config_path)

        user_config = Configuration._create_from_config_file(_user_config_path)
        environment_config = Configuration._create_from_environment()
        argument_config = Configuration._create_from_arguments(application_arguments)
        default_config = Configuration._create_from_defaults()

        return Configuration._merge_configs(default_config, system_config, user_config, environment_config,
                                            argument_config).normalized()

    def normalized(self) -> Self:
        """
        Returns a normalized version of the configuration (e.g., with None values removed).
        """
        normalized_config = Configuration()

        for key, value in self.__dict__.items():
            if value is not None:
                setattr(normalized_config, key, value)
            else:
                setattr(normalized_config, key, "")

        # Normalize paths since they may contain environment variables or user directories
        normalized_config.download_cache_path = str(Path(self.download_cache_path).expanduser().resolve())
        normalized_config.package_workspace_path = str(Path(self.package_workspace_path).expanduser().resolve())
        normalized_config.package_artifact_path = str(Path(self.package_artifact_path).expanduser().resolve())
        normalized_config.repository_cache_path = str(Path(self.repository_cache_path).expanduser().resolve())

        return normalized_config

    def dump_config(self):
        """
        Get the effective config values
        """
        config = ""
        for key, value in self.__dict__.items():
            config += f"{key}={value}\n"

        return config

    def ensure_executables_exist(self):
        """
        Ensure that all required executables are available in the system.
        """
        executables = [
            self.fakeroot_executable,
            self.shell_executable
        ]

        for executable in executables:
            if not exists(executable):
                raise FileNotFoundError(f"Required executable not found: {executable}.")

            # Check if the path to the executable is executable on the filesystem
            if not access(executable, X_OK):
                raise PermissionError(f"Executable {executable} is not executable. Please check permissions.")

    @classmethod
    def _create_from_config_file(cls, path: str) -> Self | None:
        """
        Load configuration from a file.
        This method should be implemented to read from a specific configuration file.
        """

        logger.debug(f"Loading config file: {path}")

        if not exists(path):
            logger.warning(f"Configuration file does not exist: {path}")
            return Configuration()

        config = ConfigParser()
        config.read(path, encoding="utf-8")

        streams = config.get("repository", "package_streams", fallback="").split(",")

        if not streams or streams == [""]:
            streams = None

        return Configuration(
            suppress_build_output=config.getboolean("general", "suppress_build_output", fallback=None),
            show_download_progress=config.getboolean("general", "show_download_progress", fallback=None),
            repository_cache_path=config.get("general", "repository_cache_path", fallback=None),
            download_cache_path=config.get("general", "download_cache_path", fallback=None),
            target_architecture=config.get("environment", "target_architecture", fallback=None),
            c_flags=config.get("build", "c_flags", fallback=None),
            cpp_flags=config.get("build", "cpp_flags", fallback=None),
            ld_flags=config.get("build", "ld_flags", fallback=None),
            make_flags=config.get("build", "make_flags", fallback=None),
            ninja_flags=config.get("build", "ninja_flags", fallback=None),
            repositories=RepositoryRef.from_string(config.get("repository", "repositories", fallback="")),
            package_streams=streams)

    @classmethod
    def _create_from_environment(cls) -> Self:
        """
        Load configuration from environment variables.
        This method should be implemented to read from environment variables.
        """
        return Configuration(
            target_architecture=environ.get("ALPACA_TARGET_ARCHITECTURE"),
            c_flags=environ.get("ALPACA_C_FLAGS"),
            cpp_flags=environ.get("ALPACA_CXX_FLAGS"),
            ld_flags=environ.get("ALPACA_LD_FLAGS")
        )

    @classmethod
    def _create_from_defaults(cls) -> Self:
        work_dir = getcwd()

        return Configuration(
            package_workspace_path=join(work_dir, "build"),
            package_artifact_path=work_dir,
            download_cache_path="/var/lib/alpaca/downloads",
            repository_cache_path="/var/lib/alpaca/cache",
            prefix="/",
            fakeroot_executable=_default_fakeroot_executable,
            shell_executable=_default_shell_executable,
            cat_executable=_default_cat_executable,
            recipe_file_extension=_default_recipe_file_extension,
            package_file_extension=_default_package_file_extension
        )

    @classmethod
    def _create_from_arguments(cls, args: Namespace) -> Self:
        """
        Load configuration from command line arguments.
        This method should be implemented to read from command line arguments.
        """
        return Configuration(
            verbose_output=getattr(args, "verbose", None),
            suppress_build_output=getattr(args, "quiet", None),
            keep_build_directory=getattr(args, "keep", None),
            prefix=getattr(args, "target", None),
            skip_package_check=getattr(args, "no_check", None),
            force_download=getattr(args, "download", None),
            package_workspace_path=getattr(args, "workdir", None),
            package_artifact_path=getattr(args, "output", None),
            package_delete_workspace=getattr(args, "delete_workdir", None)
        )

    @classmethod
    def _merge_configs(cls, *configs: Self) -> Self:
        """
        Merge multiple Config instances into one.
        The last non-None value for each attribute will be used.
        """

        merged = Configuration()

        for config in configs:
            if config is None:
                continue

            for key, value in config.__dict__.items():
                if value is not None:
                    setattr(merged, key, value)

        return merged
