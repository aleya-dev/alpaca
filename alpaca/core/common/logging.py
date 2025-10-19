from logging import DEBUG, INFO, WARNING, ERROR, CRITICAL, Logger, addLevelName, Formatter, setLoggerClass, getLogger, \
    StreamHandler
import sys
from typing import Optional

VERBOSE = 5
addLevelName(VERBOSE, "VERBOSE")

HEADER = INFO - 1
addLevelName(HEADER, "HEADER")

STDOUT = HEADER - 1
addLevelName(STDOUT, "STDOUT")

STDERR = STDOUT - 1
addLevelName(STDERR, "STDERR")

_LIGHT_BLUE = "\033[94m"
_CYAN = "\033[96m"
_GREEN = "\033[92m"
_YELLOW = "\033[93m"
_RED = "\033[91m"
_MAGENTA = "\033[95m"
_BOLD = "\033[1m"
_RESET = "\033[0m"

class AlpacaLogger(Logger):
    def verbose(self, msg: str, *args, **kwargs) -> None:
        if self.isEnabledFor(VERBOSE):
            self._log(VERBOSE, msg, args, **kwargs)

    def header(self, msg: str, *args, **kwargs) -> None:
        if self.isEnabledFor(HEADER):
            self._log(HEADER, msg, args, **kwargs)

    def stdout(self, msg: str, *args, **kwargs) -> None:
        if self.isEnabledFor(STDOUT):
            self._log(STDOUT, msg, args, **kwargs)

    def stderr(self, msg: str, *args, **kwargs) -> None:
        if self.isEnabledFor(STDERR):
            self._log(STDERR, msg, args, **kwargs)


class _ColoredFormatter(Formatter):
    def format(self, record):
        message = record.getMessage()

        if record.levelno == VERBOSE:
            fmt = f"{_LIGHT_BLUE}[VERBOSE] {message}{_RESET}"
        elif record.levelno == DEBUG:
            fmt = f"{_CYAN}[DEBUG] {message}{_RESET}"
        elif record.levelno == INFO:
            fmt = f"-- {message}"
        elif record.levelno == HEADER:
            fmt = f"{_BOLD}{_GREEN}==={_RESET} {message} {_GREEN}==={_RESET}"
        elif record.levelno == STDOUT:
            fmt = f"{_RESET}{message}"
        elif record.levelno == STDERR:
            fmt = f"{_YELLOW}{message}{_RESET}"
        elif record.levelno == WARNING:
            fmt = f"{_YELLOW}!! [WARNING] {message}{_RESET}"
        elif record.levelno == ERROR:
            fmt = f"{_RED}!! [ERROR] {message}{_RESET}"
        elif record.levelno == CRITICAL:
            fmt = f"{_MAGENTA}!! [FATAL] {message}{_RESET}"
        else:
            fmt = f"?? {message}"

        return fmt


def setup_logging(level: int = INFO, stream=sys.stdout) -> AlpacaLogger:
    """
    Initialize colored logging for the entire application.
    Returns the 'alpaca' logger.
    """
    setLoggerClass(AlpacaLogger)

    root = getLogger()
    if not root.handlers:
        handler = StreamHandler(stream)
        handler.setFormatter(_ColoredFormatter("%(levelname)s: %(message)s"))
        root.addHandler(handler)

    root.setLevel(level)

    return getLogger("alpaca")  # type: ignore[return-value]


def get_logger(name: Optional[str] = None) -> AlpacaLogger:
    """Get a namespaced logger under 'alpaca' with full type support."""
    full_name = "alpaca" if name is None else f"alpaca.{name}"
    return getLogger(full_name)  # type: ignore[return-value]


def _patch_logger_verbose():
    Logger.verbose = AlpacaLogger.verbose
    Logger.header = AlpacaLogger.header
    Logger.stdout = AlpacaLogger.stdout
    Logger.stderr = AlpacaLogger.stderr


_patch_logger_verbose()
