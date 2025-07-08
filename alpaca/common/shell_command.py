import io
import subprocess
import threading
from enum import Enum
from os import environ
from pathlib import Path

from alpaca.common.logging import logger
from alpaca.configuration import Configuration

_bash_executable = "/usr/bin/bash"
_fakeroot_executable = "/usr/bin/fakeroot"


class StreamType(Enum):
    """
    Enum representing the type of output stream
    """

    STDOUT = "stdout"
    STDERR = "stderr"


class ShellCommandResult:
    def __init__(self, error_code: int, stdout: str, stderr: str):
        self.error_code: int = error_code
        self.stdout: str = stdout
        self.stderr: str = stderr


class ShellCommand:
    @staticmethod
    def _stream_output(stream, print_output: bool, output_string: io.StringIO, destination: StreamType):
        for line in iter(stream.readline, ""):
            if print_output:
                if destination == StreamType.STDOUT:
                    logger.info(line.replace('\n', ''))
                elif destination == StreamType.STDERR:
                    logger.error(line.replace('\n', ''))

            output_string.write(line)

        stream.close()

    @staticmethod
    def exec(configuration: Configuration, command: str, environment: dict[str, str] | None = None,
             working_directory: Path | None = None, print_output: bool = True, throw_on_error: bool = False,
             use_fakeroot: bool = False) -> ShellCommandResult:
        """Execute a command in the shell

        Args:
            configuration (Configuration): The configuration to use for the command execution
            command (str): The command to execute
            environment (dict[str, str], optional): A dictionary of environment variables to set. Defaults to None.
            working_directory (str, optional): The working directory to execute the command in. Defaults to None.
            print_output (bool, optional): Whether to print the output of the command. Defaults to True.
            throw_on_error (bool, optional): Whether to throw an exception if the command fails. Defaults to False.
            use_fakeroot (bool, optional): Whether to use fakeroot for the command. Defaults to False.

        Returns:
            tuple[str, str]: A tuple containing the stdout and stderr output of the command
        """

        env = environ.copy()

        if environment is not None:
            env.update(environment)

        args = []

        if use_fakeroot:
            logger.info("Entering fakeroot...")
            args.append(configuration.fakeroot_executable)

        args.append(configuration.shell_executable)
        args.append("-c")
        args.append(command)

        process = subprocess.Popen(args=args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1,
                                   universal_newlines=True, cwd=working_directory, env=env)

        stdout_str = io.StringIO()
        stderr_str = io.StringIO()

        stdout_thread = threading.Thread(target=ShellCommand._stream_output,
                                         args=(process.stdout, print_output, stdout_str, StreamType.STDOUT))
        stderr_thread = threading.Thread(target=ShellCommand._stream_output,
                                         args=(process.stderr, print_output, stderr_str, StreamType.STDERR))

        stdout_thread.start()
        stderr_thread.start()

        error_code = process.wait()

        stdout_thread.join()
        stderr_thread.join()

        if throw_on_error and error_code != 0:
            logger.fatal(stderr_str.getvalue())
            raise Exception(f"Command failed with error code {error_code}.")

        return ShellCommandResult(error_code, stdout_str.getvalue(), stderr_str.getvalue())

    @staticmethod
    def exec_get_value(configuration: Configuration, command: str, working_directory: str | None = None,
                       environment: dict[str, str] | None = None, ) -> str:
        """Execute a command in the shell and return the stdout. Expects a single line of output.

        Args:
            configuration (Configuration): The configuration to use for the command execution
            command (str): The command to execute
            working_directory (str, optional): The working directory to execute the command in. Defaults to None.
            environment (dict[str, str], optional): A dictionary of environment variables to set. Defaults to None.

        Returns:
            str: The stdout of the command, trimmed with the newline removed
        """

        result = ShellCommand.exec(configuration=configuration, command=command, environment=environment,
                                   working_directory=working_directory, print_output=False, throw_on_error=True)

        return result.stdout.strip()
