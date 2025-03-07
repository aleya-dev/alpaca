from alpaca.logging import logger
from numbers import Number
from urllib.parse import urlparse
import urllib.request
import hashlib
import tarfile
import shutil
import os
import sys


def get_full_path(path: str) -> str:
    """
    Get the full absolute path of a file or directory, expanding environment variables and user home directories

    Args:
        path (str): The path to expand; can be a file or directory.
                    Can contain environment variables and ~ for the user home directory

    Returns:
        str: The full absolute path of the file or directory
    """

    return os.path.abspath(os.path.expandvars(os.path.expanduser(path)))


def show_progress_bar(current: Number, total: Number, bar_length: int = 40) -> str:
    """
    Displays a progress bar

    Args:
        current (Number): The current progress
        total (Number): The total progress
        bar_length (int, optional): The length of the progress bar. Defaults to 40.
    """
    percent = current / total * 100
    block = int(round(bar_length * current / total))
    progress = "#" * block + "-" * (bar_length - block)
    sys.stdout.write(f"\r[{progress}] {percent:.1f}% ({current}/{total} bytes)")
    sys.stdout.flush()

    if current == total:
        sys.stdout.write("\n")
        sys.stdout.flush()


def is_url(url: str) -> bool:
    """
    Check if a string is a URL

    Args:
        url (str): The string to check

    Returns:
        bool: True if the string is a URL, False otherwise
    """
    return urlparse(url).scheme != ""


def is_file_path(path: str) -> bool:
    """
    Check if a string is a file path

    Args:
        path (str): The string to check

    Returns:
        bool: True if the string is a file path, False otherwise
    """
    return os.path.isfile(path)


def download_file(url: str, destination_dir: str, show_progress: bool = True) -> str:
    """
    Download a file from a URL to a destination directory

    Args:
        url (str): The URL of the file to download
        destination_dir (str): The directory to save the file to
        show_progress (bool, optional): Whether to show a progress bar while downloading. Defaults to True.

    Returns:
        str: The name of the downloaded file
    """

    parsed_url = urlparse(url)
    file_name = os.path.basename(parsed_url.path)
    destination_path = os.path.join(destination_dir, file_name)

    urllib.request.urlretrieve(
        url,
        destination_path,
        reporthook=lambda block_num, block_size, total_size: (
            show_progress_bar(block_num * block_size, total_size)
            if show_progress
            else None
        ),
    )

    # Hack; the reporthook doesn't report the final block, so we need to print the final progress
    if show_progress:
        show_progress_bar(
            os.path.getsize(destination_path), os.path.getsize(destination_path)
        )

    return file_name


def is_tarfile(file_path: str) -> bool:
    """
    Check if a file is a tar archive

    Args:
        file_path (str): The path of the file to check

    Returns:
        bool: True if the file is a tar archive, False otherwise
    """
    return tarfile.is_tarfile(file_path)


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


def check_file_hash_from_string(path: str, hash: str) -> bool:
    """
    Check if a file exists and has the correct hash

    Args:
        path (str): The path to the file
        hash (str): The expected hash of the file

    Returns:
        bool: True if the file exists and has the correct hash, False otherwise
    """
    if not os.path.exists(path):
        logger.error(f"File {path} does not exist. Could not verify sha256 hash.")
        return False

    file_hash = get_file_hash(path)

    if file_hash != hash:
        logger.error(
            f"File {path} has hash {file_hash}, expected {hash}. File may be corrupt."
        )
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


def create_empty_directory(path: str):
    """
    Create an empty directory

    Args:
        path (str): The path of the directory to (re)create
    """

    if os.path.exists(path):
        logger.verbose(f"Removing existing directory {path}")
        shutil.rmtree(path)

    logger.verbose(f"Creating directory {path}")
    os.makedirs(path)


def extract_tar(file_path: str, destination_dir: str):
    """
    Untar a file to a destination directory

    Args:
        file_path (str): The path of the tar file to extract
        destination_dir (str): The directory to extract the tar file to
    """

    logger.verbose(f"Extracting {file_path} to {destination_dir}...")

    with tarfile.open(file_path, "r") as tar:
        tar.extractall(destination_dir)

    logger.verbose(f"File {file_path} extracted to {destination_dir}")


def compress_tar(directory: str, archive_path: str):
    """
    Compress a directory to a tar.xz archive

    Args:
        directory (str): The source directory to archive
        archive_path (str): The path of the target archive
    """

    logger.verbose(f"Archiving directory {directory} to {archive_path}...")

    files = []
    for root, _, filenames in os.walk(directory):
        for filename in filenames:
            files.append(os.path.join(root, filename))

    with tarfile.open(archive_path, "w:xz") as tar:
        for file in files:
            tar.add(file, arcname=os.path.relpath(file, directory))

    logger.verbose(f"Directory {directory} archived to {archive_path}")
