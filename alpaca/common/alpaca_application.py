import importlib.metadata
from argparse import ArgumentParser, Namespace
from os import getuid

__version__ = importlib.metadata.version("aleya-alpaca")

from typing import Callable

from alpaca.common.logging import enable_verbose_logging, logger
from alpaca.configuration.configuration import Configuration


def _create_arg_parser_for_application(application_name: str) -> ArgumentParser:
    parser = ArgumentParser(
        description=f"AlpaCA {application_name} - The Aleya Package Configuration Assistant ({__version__})")

    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose output")

    parser.add_argument("--version", action="version", version=f"AlpaCA version: {__version__}")

    return parser


def _create_configuration_for_application(args: Namespace):
    return Configuration.create_application_config(args)


def handle_main(application_name: str, require_root: bool, disallow_root: bool,
                create_arguments_callback: Callable[[ArgumentParser], ArgumentParser],
                main_function_callback: Callable[[Namespace, Configuration], None]):
    """
    A decorator to handle the main function of an application, ensuring that it is run with the correct user permissions.

    Args:
        application_name (str): The name of the application.
        require_root (bool): If True, the application must be run as root.
        disallow_root (bool): If True, the application must not be run as root.
        create_arguments_callback (function): A function to create the argument parser for the application.
        main_function_callback (function): The main function of the application.
    """
    try:
        parser = _create_arg_parser_for_application(application_name)
        parser = create_arguments_callback(parser)

        args = parser.parse_args()

        # Hack to ensure that verbose logs from the configuration module are printed
        if args.verbose:
            enable_verbose_logging()

        config = _create_configuration_for_application(args)

        config.ensure_executables_exist()

        if config.verbose_output:
            enable_verbose_logging()

        is_root = getuid() == 0

        if require_root and not is_root:
            raise PermissionError(f"Running '{application_name}' requires root privileges. Please run as root.")

        if disallow_root and is_root:
            raise PermissionError(f"Running '{application_name}' as root is not allowed. Please run as a normal user.")

        logger.debug("This software is provided under GNU GPL v3.0")
        logger.debug("This software comes with ABSOLUTELY NO WARRANTY")
        logger.debug("This software is free software, and you are welcome to redistribute it under certain conditions")
        logger.debug("For more information, visit https://www.gnu.org/licenses/gpl-3.0.html")

        main_function_callback(args, config)

    except Exception as e:
        logger.fatal(f"An error has occurred: {e}")
        exit(1)
