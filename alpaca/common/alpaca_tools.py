import sys
from os.path import abspath, dirname

from alpaca.common.logging import logger


def get_alpaca_tool_command(name: str) -> str:
    """
    Get the command for a specific Alpaca tool. The tool path that is returned
    is based on how the current script is executed.
    """

    command: str = ""

    if sys.argv[0].endswith(".py"):
        full_module_path = dirname(abspath(sys.argv[0]))
        logger.debug(f"Running in Dev mode. Using script path: {full_module_path}")
        command += f"PYTHONPATH={full_module_path} "

    command += f'''python3 -c "from alpaca.{name}.{name}_main import main; main()" '''

    return command
