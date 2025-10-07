import logging
import sys
from typing import Optional

VERBOSE = 5
logging.addLevelName(VERBOSE, "VERBOSE")

_COLORS = {
    "VERBOSE": "\033[94m",  # bright blue
    "DEBUG": "\033[96m",  # cyan
    "INFO": "",  # default
    "WARNING": "\033[93m",  # yellow
    "ERROR": "\033[91m",  # red
    "CRITICAL": "\033[95m",  # magenta
    "RESET": "\033[0m",
}


class AlpacaLogger(logging.Logger):
    """Custom logger with 'verbose' level and IDE-friendly typing."""

    def verbose(self, msg: str, *args, **kwargs) -> None:
        if self.isEnabledFor(VERBOSE):
            self._log(VERBOSE, msg, args, **kwargs)


class _ColoredFormatter(logging.Formatter):
    def format(self, record):
        color = _COLORS.get(record.levelname, _COLORS["RESET"])
        message = super().format(record)
        return f"{color}{message}{_COLORS['RESET']}"


def setup_logging(level: int = logging.INFO, stream=sys.stdout) -> AlpacaLogger:
    """
    Initialize colored logging for the entire application.
    Returns the 'alpaca' logger.
    """
    logging.setLoggerClass(AlpacaLogger)

    root = logging.getLogger()
    if not root.handlers:
        handler = logging.StreamHandler(stream)
        handler.setFormatter(_ColoredFormatter("%(levelname)s: %(message)s"))
        root.addHandler(handler)

    root.setLevel(level)

    return logging.getLogger("alpaca")  # type: ignore[return-value]


def get_logger(name: Optional[str] = None) -> AlpacaLogger:
    """Get a namespaced logger under 'alpaca' with full type support."""
    full_name = "alpaca" if name is None else f"alpaca.{name}"
    return logging.getLogger(full_name)  # type: ignore[return-value]


def _patch_logger_verbose():
    def verbose(self, msg, *args, **kwargs):
        if self.isEnabledFor(VERBOSE):
            self._log(VERBOSE, msg, args, **kwargs)

    logging.Logger.verbose = verbose


_patch_logger_verbose()
