def is_aleya_linux_host() -> bool:
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
