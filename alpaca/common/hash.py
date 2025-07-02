import hashlib
import os

from alpaca.common.logging import logger


def get_file_hash(path: str) -> str:
    """
    Get the sha256 hash of a file

    Args:
        path (str): The path to the file

    Returns:
        str: The sha256 hash of the file
    """
    with open(path, "rb") as file:
        return hashlib.sha256(file.read()).hexdigest()


def write_file_hash(path: str):
    """
    Write the sha256 hash of a file to a file with a .sha256 extension

    Args:
        path (str): The path to the file
        hash_file_path (str): The path to write the hash to
    """
    with open(f"{path}.sha256", "w") as file:
        file.write(get_file_hash(path))


def check_file_hash_from_string(path: str, expected_hash: str) -> bool:
    """
    Check if a file exists and has the correct hash

    Args:
        path (str): The path to the file
        expected_hash (str): The expected hash of the file

    Returns:
        bool: True if the file exists and has the correct hash, False otherwise
    """
    if not os.path.exists(path):
        logger.error(f"File {path} does not exist. Could not verify sha256 hash.")
        return False

    file_hash = get_file_hash(path)

    if file_hash != expected_hash:
        logger.error(f"File {path} has hash {file_hash}, expected {expected_hash}. File may be corrupt.")
        return False

    return True


def check_file_hash_from_file(path: str) -> bool:
    """
    Check if a file exists and has the correct hash

    Args:
        path (str): The path to the file

    Returns:
        bool: True if the file exists and has the correct hash, False otherwise
    """
    sha_file_path = f"{path}.sha256"

    if not os.path.exists(sha_file_path):
        logger.error(f"Hash file {sha_file_path} does not exist. Could not verify sha256 hash.")
        return False

    with open(sha_file_path, "r") as file:
        expected_hash = file.read().strip()

    return check_file_hash_from_string(path, expected_hash)
