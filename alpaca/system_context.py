import importlib.metadata
from alpaca.configuration import Configuration


__version__ = importlib.metadata.version("aleya-alpaca")


class SystemContext:
    def __init__(self, configuration: Configuration):
        self.configuration = configuration
