def ask_user_confirmation(message: str, default: bool = False) -> bool:
    """
    Ask the user for confirmation with a yes/no question.

    Args:
        message (str): The message to display to the user.
        default (bool): If True, the default answer is 'yes', otherwise it is 'no'.

    Returns:
        bool: True if the user confirms, False otherwise.
    """

    if default:
        prompt = f"{message} [Y/n]: "
    else:
        prompt = f"{message} [y/N]: "

    while True:
        try:
            response = input(prompt).strip().lower()
            if response in ('y', 'yes'):
                return True
            elif response in ('n', 'no'):
                return False
            elif response == '':
                return default
            else:
                print("Please respond with 'yes' or 'no'.")
        except EOFError:
            print("\nInput interrupted. Exiting.")
            exit(1)
