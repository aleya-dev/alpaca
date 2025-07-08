import hashlib
import os
from os.path import basename
from pathlib import Path

from alpaca.common.logging import logger


def get_file_hash(path: str | Path) -> str:
    """
    Get the sha256 hash of a file

    Args:
        path (str | Path): The path to the file

    Returns:
        str: The sha256 hash of the file
    """
    with open(path, "rb") as file:
        return hashlib.sha256(file.read()).hexdigest()


def write_file_hash(path: str | Path):
    """
    Write the sha256 hash of a file to a file with a .sha256 extension

    Args:
        path (str | Path): The path to the file
    """

    logger.debug(f"Writing sha256 hash for {path}")

    filename = basename(path)

    with open(f"{path}.sha256", "w") as file:
        file.write(get_file_hash(path))
        file.write("  ")
        file.write(filename)
        file.write("\n")

    logger.debug(f"Sha256 hash for {path} written to {path}.sha256")


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


def check_file_hash_from_file(path: str | Path) -> bool:
    """
    Check if a file exists and has the correct hash

    Args:
        path (str | Path): The path to the file

    Returns:
        bool: True if the file exists and has the correct hash, False otherwise
    """
    sha_file_path = f"{path}.sha256"

    if not os.path.exists(sha_file_path):
        logger.error(f"Hash file {sha_file_path} does not exist. Could not verify sha256 hash.")
        return False

    with open(sha_file_path, "r") as file:
        line = file.read().strip()

    parts = line.split("  ")

    if len(parts) != 2:
        logger.error(f"Hash file {sha_file_path} is malformed. Expected format: '<hash>  <filename>'.")
        return False

    expected_hash, filename = parts

    if filename != basename(path):
        logger.error(f"Hash file {sha_file_path} does not match the file {path}. Expected filename {filename}.")
        return False

    return check_file_hash_from_string(path, expected_hash)
