from alpaca.utils import get_full_path, singleton
from alpaca.logging import logger
from alpaca.repository import Repository, RepositoryType
import os
import configparser


@singleton
class Configuration:
    def __init__(self):
        logger.debug("Initializing configuration")

        config_file_path = self._get_config_file_path()

        # Todo: This should look in various locations for the configuration file
        # and should also be able to be overridden by environment variables and command line arguments
        config = configparser.ConfigParser()

        if config_file_path is not None:
            config.read(config_file_path, encoding="utf-8")

        self.verbose_logging = False

        self.suppress_build_output = config.getboolean(
            "general", "suppress_build_output", fallback="false"
        )

        self.show_download_progress = config.getboolean(
            "general", "show_download_progress", fallback="true"
        )

        self.target_architecture = config.get(
            "environment", "target_architecture", fallback="x86_64"
        )

        self.c_flags = config.get("build", "c_flags", fallback="-O2")
        self.cpp_flags = config.get("build", "cpp_flags", fallback="-O2")
        self.ld_flags = config.get("build", "ld_flags", fallback="")
        self.make_flags = config.get("build", "make_flags", fallback="")
        self.ninja_flags = config.get("build", "ninja_flags", fallback="")

        self.force_build_from_source = False
        self.keep_intermediates_on_failure = False

        self.is_dry_run = False
        self.skip_check = False

        self.is_aleya_linux_host = self._check_aleya_linux_host()
        self.user_is_root = os.getuid() == 0

        self.install_target = "/"
        self.data_directory = "/var/lib/alpaca"

        self.repositories: list[Repository] = []
        self._parse_repositories(config)

        self.package_streams: list[str] = []
        self._parse_package_streams(config)

    def get_repository_base_path(self) -> str:
        return os.path.join(self.data_directory, "repositories")

    def get_workspace_base_path(self) -> str:
        return os.path.join(self.data_directory, "workspace")

    def get_package_local_binary_cache_base_path(self) -> str:
        return os.path.join(self.data_directory, "bincache", "local")

    def dump_config(self):
        print(
            f"""[general]
suppress_build_output={self.suppress_build_output}
show_download_progress={self.show_download_progress}

[environment]
target_architecture={self.target_architecture}

[repository]
repositories={self._get_repositories_config_entry()}
package_streams={self._get_package_stream_config_entry()}

[build]
c_flags={self.c_flags}
cpp_flags={self.cpp_flags}
ld_flags={self.ld_flags}
make_flags={self.make_flags}
ninja_flags={self.ninja_flags}
"""
        )

    def _get_repositories_config_entry(self):
        str = ""

        for repo in self.repositories:
            if repo.get_type() == RepositoryType.GIT:
                str += f"git+{repo.get_defined_path()},"
            elif repo.get_type() == RepositoryType.LOCAL:
                str += f"local+{repo.get_defined_path()},"

        if len(str) > 0:
            str = str[:-1]

        return str

    def _parse_repositories(self, config: configparser.ConfigParser):
        repo_list_str = config.get("repository", "repositories", fallback="")

        if repo_list_str == "":
            self.repositories.append(
                Repository(
                    "git+https://github.com/aleya-dev/aleya-packages.git",
                    self.get_repository_base_path(),
                )
            )
            return

        repo_list = repo_list_str.split(",")

        logger.verbose(f"Parsing repositories: {repo_list}")

        for repo in repo_list:
            self.repositories.append(Repository(repo, self.get_repository_base_path()))

    def _get_package_stream_config_entry(self):
        return ",".join(self.package_streams)

    def _parse_package_streams(self, config: configparser.ConfigParser):
        self.package_streams = config.get(
            "repository", "package_streams", fallback="core"
        ).split(",")

    @staticmethod
    def _get_config_file_path() -> str:
        if os.environ.get("ALEYA_CONFIG") is not None:
            logger.debug(
                "Using configuration file specified in ALEYA_CONFIG environment variable"
            )

            aleya_config_env_path = os.environ.get("ALEYA_CONFIG")
            if os.path.exists(aleya_config_env_path):
                return os.environ.get("ALEYA_CONFIG")
            else:
                logger.warning(
                    "Configuration file specified in ALEYA_CONFIG environment "
                    f" variable does not exist: {aleya_config_env_path}. Ignoring"
                )

        home_config_path = get_full_path("~/.alpaca")
        logger.debug(f"Looking for configuration file at {home_config_path}")
        if os.path.exists(home_config_path):
            logger.debug(f"Using configuration file found at {home_config_path}")
            return home_config_path

        global_config_path = get_full_path("/etc/alpaca.conf")
        logger.debug(f"Looking for configuration file at {global_config_path}")
        if os.path.exists(global_config_path):
            logger.debug(f"Using configuration file found at {global_config_path}")
            return global_config_path

        # Get the current working directory
        local_config_path = os.path.join(os.getcwd(), "alpaca.conf")
        logger.debug(f"Looking for configuration file at {local_config_path}")
        if os.path.exists(local_config_path):
            logger.debug(f"Using local config file found at {local_config_path}")
            return local_config_path

    @staticmethod
    def _check_aleya_linux_host() -> bool:
        """
        Check if the host system is Aleya Linux by using a very simple check on the /etc/os-release file
        This helps reduce the risk of accidental installation on non-Aleya Linux systems; likely breaking them.

        Returns:
            bool: True if the host system is Aleya Linux, False otherwise
        """
        with open("/etc/os-release") as f:
            for line in f:
                if line.startswith("ID="):
                    return line.strip() == "ID=aleya"

        return False
