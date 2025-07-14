import logging

logger = None

VERBOSE = 5
logging.addLevelName(VERBOSE, "VERBOSE")

_COLORS = {
    "VERBOSE": "\033[94m",
    "DEBUG": "\033[96m",
    "INFO": "",
    "WARNING": "\033[93m",
    "ERROR": "\033[91m",
    "CRITICAL": "\033[95m",
    "RESET": "\033[0m"
}


class _ColoredFormatter(logging.Formatter):
    def format(self, record):
        log_color = _COLORS.get(record.levelname, _COLORS["RESET"])
        log_message = super().format(record)
        return f"{log_color}{log_message}{_COLORS['RESET']}"


def _log_verbose(self, message, *args, **kwargs):
    if self.isEnabledFor(VERBOSE):
        self._log(VERBOSE, message, args, **kwargs)


def suppress_logging():
    """
    Suppresses all logging output to only errors
    """
    logger.setLevel(logging.ERROR)


def enable_verbose_logging():
    if logger.level == VERBOSE:
        return

    logger.setLevel(VERBOSE)
    logger.verbose("Verbose output enabled")


def setup_logger() -> logging.Logger:
    logging.Logger.verbose = _log_verbose

    log = logging.getLogger("alpaca")
    log.setLevel(logging.INFO)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(_ColoredFormatter("%(message)s"))
    log.addHandler(console_handler)

    return log


logger = setup_logger()
