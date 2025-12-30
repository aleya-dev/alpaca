import importlib.metadata
from argparse import Namespace
from configparser import ConfigParser
from enum import Enum
from os import environ
from os.path import exists, abspath, expandvars, expanduser
from typing import Self

from alpaca.core.common.logging import get_logger
from alpaca.core.repository_ref import RepositoryRef

_system_config_path = "/etc/alpaca.conf"
_user_config_path = abspath(expandvars(expanduser("~/.alpaca")))

"""Environment variable name for specifying a custom configuration file path."""
_alpaca_config_env_var = "ALPACA_CONFIG"

_default_recipe_file_extension = ".recipe.sh"
_default_package_info_file_extension = ".package-info.json"
_default_package_file_extension = ".alpaca-package.tgz"
_default_package_database_file_extension = ".package_info.tgz"
_default_package_repository = "web+https://packages.ruadeil.lgbt/packages/"
_default_package_streams = ["core"]

logger = get_logger(__name__)

__version__ = importlib.metadata.version("aleya-alpaca")


class ConfigurationType(Enum):
    """
    Enum representing the type of output stream
    """

    NONE = ""  # No configuration, used for empty values
    SYSTEM = "SYSTEM"  # e.g., /etc/alpaca.conf
    USER = "USER"  # e.g., ~/.alpaca
    ENVCONF = "ENVCONF"  # Config file specified in the environment variable ALPACA_CONFIG
    ARGUMENTS = "ARGUMENTS"  # Command line arguments passed to the application
    ENVIRONMENT = "ENVIRONMENT"  # Environment variables (e.g., ALPACA_CONFIG)
    DEFAULTS = "DEFAULTS"  # Default values for the configuration, used if no other configuration is provided
    MERGED = "MERGED"  # Merged configuration from all sources


def _configuration_type_to_string(config_type: ConfigurationType) -> str:
    """
    Convert a ConfigurationType to a string representation.
    """
    if config_type == ConfigurationType.NONE:
        return "None"
    elif config_type == ConfigurationType.SYSTEM:
        return "System config file"
    elif config_type == ConfigurationType.USER:
        return "User config file"
    elif config_type == ConfigurationType.ENVCONF:
        return "EnvVar specified config file"
    elif config_type == ConfigurationType.ARGUMENTS:
        return "Arguments"
    elif config_type == ConfigurationType.ENVIRONMENT:
        return "Environment variables"
    elif config_type == ConfigurationType.DEFAULTS:
        return "Default value"
    elif config_type == ConfigurationType.MERGED:
        return "Merged"
    else:
        raise ValueError(f"Unknown configuration type: {config_type}")


class Configuration:
    """
    Configuration class for managing build settings and options.

    Attributes:
        c_flags (str | None): C compiler flags.
        cpp_flags (str | None): C++ compiler flags.
        ld_flags (str | None): Linker flags.
        make_flags (str | None): Make flags.
        ninja_flags (str | None): Ninja flags.

        repositories (list[RepositoryRef] | None): List of repositories to use.
        package_streams (list[str] | None): List of package streams to use.
    """

    def __init__(self, config_type: ConfigurationType, **kwargs) -> None:
        """
        Initialize the Configuration instance.

        Args:
            config_type (ConfigurationType): The type of configuration being created.
            **kwargs: Additional keyword arguments for configuration options.
                      Values will be set to None if not provided.
        """

        self.type = config_type

        self.c_flags: str | None = kwargs.get('c_flags', None)
        self.cpp_flags: str | None = kwargs.get('cpp_flags', None)
        self.ld_flags: str | None = kwargs.get('ld_flags', None)
        self.make_flags: str | None = kwargs.get('make_flags', None)
        self.ninja_flags: str | None = kwargs.get('ninja_flags', None)

        self.package_repositories: list[RepositoryRef] | None = kwargs.get('package_repositories', None)
        self.package_streams: list[str] | None = kwargs.get('package_streams', None)

        self.recipe_repositories: list[RepositoryRef] | None = kwargs.get('recipe_repositories', None)
        self.recipe_streams: list[str] | None = kwargs.get('recipe_streams', None)

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

        logger.debug("Creating application configuration...")

        config_env_var = environ.get(_alpaca_config_env_var, None)
        if config_env_var is not None:
            logger.debug(f"Using configuration file specified in {_alpaca_config_env_var} environment variable")

            alpaca_config_path = config_env_var
            if exists(alpaca_config_path):
                system_config = Configuration._create_from_config_file(ConfigurationType.ENVCONF, alpaca_config_path)
            else:
                logger.warning(f"Configuration file specified in {_alpaca_config_env_var} environment "
                               f" variable does not exist: {alpaca_config_path}.")

        if system_config is None:
            logger.debug(f"Loading system config file: {_system_config_path}")
            system_config = Configuration._create_from_config_file(ConfigurationType.SYSTEM, _system_config_path)

        user_config = Configuration._create_from_config_file(ConfigurationType.USER, _user_config_path)
        environment_config = Configuration._create_from_environment()
        argument_config = Configuration._create_from_arguments(application_arguments)
        default_config = Configuration._create_from_defaults()

        merged = Configuration._merge_configs(default_config, system_config, user_config, environment_config,
                                              argument_config)

        Configuration._dump_config_log(merged)
        return merged

    def dump_config(self):
        """
        Get the effective config values
        """

        config = ""

        for key, value in self.__dict__.items():
            config += f"{key}={value}\n"

        return config

    def get_variables(self) -> dict[str, str]:
        """
        Get the configuration variables for the Alpaca build process.
        This function returns a dictionary containing the necessary variables for the build process,
        including the Alpaca version, artifact path, and various flags for compilation and linking.
        The variables are used to configure the build process and ensure that the correct paths and flags
        are set for the build tools.

        These variables must be expanded with the addition of those of the current context (for example the build
        context while building a package).

        Returns:
            dict[str, str]: A dictionary containing the variables for the build process.
        """

        variables = {"alpaca_version": __version__,
                     "alpaca_script_version": "1",
                     "c_flags": self.c_flags if self.c_flags else "",
                     "cxx_flags": self.cpp_flags if self.cpp_flags else "",
                     "ld_flags": self.ld_flags if self.ld_flags else "",
                     "make_flags": self.make_flags if self.make_flags else "",
                     "ninja_flags": self.ninja_flags if self.ninja_flags else ""}

        return variables

    @classmethod
    def _create_from_config_file(cls, config_type: ConfigurationType, path: str) -> Self | None:
        """
        Load configuration from a file.
        This method should be implemented to read from a specific configuration file.

        Args:
            config_type (ConfigurationType): The type of configuration being loaded.
            path (str): The path to the configuration file.

        Returns:
            Configuration: Configuration instance created from the file.
            None: If the file does not exist or is not readable.
        """

        logger.debug(f"Loading config file: {path}")

        if not exists(path):
            logger.warning(f"Configuration file does not exist: {path}")
            return Configuration(ConfigurationType.NONE)

        config = ConfigParser()
        config.read(path, encoding="utf-8")

        package_streams = config.get("packages", "streams", fallback="").split(",")

        if not package_streams or package_streams == [""]:
            package_streams = None

        recipe_streams = config.get("recipes", "streams", fallback="").split(",")

        if not recipe_streams or recipe_streams == [""]:
            recipe_streams = None

        return Configuration(
            config_type=config_type,
            c_flags=config.get("build", "c_flags", fallback=None),
            cpp_flags=config.get("build", "cpp_flags", fallback=None),
            ld_flags=config.get("build", "ld_flags", fallback=None),
            make_flags=config.get("build", "make_flags", fallback=None),
            ninja_flags=config.get("build", "ninja_flags", fallback=None),
            package_repositories=RepositoryRef.from_string(config.get("packages", "repositories", fallback="")),
            package_streams=package_streams,
            recipe_repositories=RepositoryRef.from_string(config.get("recipes", "repositories", fallback="")),
            recipe_streams=recipe_streams,
        )

    @classmethod
    def _create_from_environment(cls) -> Self:
        """
        Load configuration from environment variables.
        This method should be implemented to read from environment variables.

        Returns:
            Configuration: Configuration instance created from environment variables.
        """
        repos = RepositoryRef.from_string(environ.get("ALPACA_REPOSITORY", ""))

        streams = environ.get("ALPACA_STREAMS", "").split(",")
        if not streams or streams == [""]:
            streams = None
        else:
            logger.info(f"Streams were overwritten by the environment to {streams}")

        return Configuration(
            config_type=ConfigurationType.ENVIRONMENT,
            c_flags=environ.get("ALPACA_C_FLAGS"),
            cpp_flags=environ.get("ALPACA_CXX_FLAGS"),
            ld_flags=environ.get("ALPACA_LD_FLAGS"),
            make_flags=environ.get("ALPACA_MAKE_FLAGS"),
            ninja_flags=environ.get("ALPACA_NINJA_FLAGS"),
            repositories=repos if repos else None,
            package_streams=streams
        )

    @classmethod
    def _create_from_defaults(cls) -> Self:
        """
        Create a configuration instance with default values.

        Returns:
            Configuration: A configuration instance with default values, if any.
        """

        return Configuration(
            config_type=ConfigurationType.DEFAULTS,
            repositories=RepositoryRef.from_string(_default_package_repository),
            streams=_default_package_streams
        )

    @classmethod
    def _create_from_arguments(cls, args: Namespace) -> Self:
        """
        Load configuration from command line arguments.
        This method should be implemented to read from command line arguments.

        Args:
            args (Namespace): Parsed command line arguments.

        Returns:
            Configuration: Configuration instance created from command line arguments.
        """

        return Configuration(
            config_type=ConfigurationType.ARGUMENTS,
        )

    @classmethod
    def _merge_configs(cls, *configs: Self) -> Self:
        """
        Merge multiple Config instances into one.
        The last non-None value for each attribute will be used.

        Args:
            *configs (Configuration): The configurations to merge in order of precedence.
        """

        merged = Configuration(ConfigurationType.MERGED)

        for config in configs:
            for key, value in config.__dict__.items():
                if key != "type" and value is not None:
                    setattr(merged, key, value)
                    setattr(merged, f"{key}_origin", config.type)

        return merged

    @classmethod
    def _dump_config_log(cls, config: Self):
        """
        Dump the configuration to the log.

        Args:
            config (Configuration): The configuration to log.
        """

        logger.debug("Merged configuration:")

        all_keys = config.__dict__.keys()
        max_key_len = max((len(key) for key in all_keys), default=0)

        all_values = [
            str(value)
            for value in config.__dict__.values()
            if value is not None and not isinstance(value, (list, tuple))
        ]
        max_value_len = max((len(v) for v in all_values), default=0)

        for key, value in config.__dict__.items():
            if key == "type" or key.endswith("_origin"):
                continue

            type_value = getattr(config, f"{key}_origin", None)
            config_type_str = _configuration_type_to_string(type_value) if type_value else "Read-only (Implied)"

            if isinstance(value, str):
                value = f"\"{value}\""

            if value is None:
                value = "None"

            if isinstance(value, (list, tuple)):
                logger.debug(f"{key.ljust(max_key_len)} = [ {' ' * (max_value_len - 2)}({config_type_str})")
                for item in value:
                    logger.debug(f"{' ' * max_key_len}   {str(item)}")
                logger.debug(f"{' ' * max_key_len} ]")
            else:
                logger.debug(f"{key.ljust(max_key_len)} = {str(value).ljust(max_value_len)}({config_type_str})")
