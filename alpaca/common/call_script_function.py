from pathlib import Path

from alpaca.common.logging import logger
from alpaca.common.shell_command import ShellCommand
from alpaca.configuration import Configuration


def call_script_function(
        configuration: Configuration,
        recipe_path: Path,
        function_name: str,
        working_dir: Path,
        environment: dict[str, str] | None = None,
        pre_script: str | None = None,
        post_script: str | None = None,
        print_output: bool = True,
        use_fakeroot: bool = False):
    """
    Call a function in shell script, if it exists. If the function does not exist, this will do nothing.

    Args:
        configuration (Configuration): The configuration for the build process.
        recipe_path (str | Path): The path to the package script file where the function is defined.
        function_name (str): The name of the function inside the package script to call.
        working_dir (str): The working directory to execute the function in.
        environment (dict[str, str] | None, optional): Additional environment variables to set for the function call.
            Defaults to None.
        pre_script (str | None, optional): Additional script to run before the function call. Defaults to None.
        post_script (str | None, optional): Additional script to run after the function call. Defaults to None.
        print_output (bool, optional): Whether to print the output of the function. Defaults to True.
        use_fakeroot (bool, optional): Whether to use fakeroot for the command. Defaults to False.
    """

    logger.verbose(f"Calling function {function_name} in package script from {working_dir}")

    ShellCommand.exec(configuration=configuration, command=f'''
            set -e
            source {recipe_path}

            {pre_script if pre_script else ''}

            if declare -F {function_name} >/dev/null; then
                {function_name};
            else
                echo 'Skipping "{function_name}". Function not found.';
            fi

            {post_script if post_script else ''}
        ''', working_directory=working_dir,
                      environment=environment,
                      print_output=print_output,
                      throw_on_error=True, use_fakeroot=use_fakeroot)

    logger.verbose(f"####### End of script function {function_name}. #######")
