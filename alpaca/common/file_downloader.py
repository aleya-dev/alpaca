import hashlib
import urllib.request
from os import makedirs
from os.path import basename, join, getsize, exists
from pathlib import Path
from shutil import copy
from urllib.parse import urlparse

from alpaca.common.logging import logger
from alpaca.common.progress_bar import show_progress_bar
from alpaca.configuration import Configuration


def _check_download_cache_path(configuration: Configuration):
    if not exists(configuration.download_cache_path):
        logger.info(f"Creating download cache path {configuration.download_cache_path}...")
        makedirs(configuration.download_cache_path)


def _get_hash_from_string(string: str) -> str:
    hash_object = hashlib.sha256()
    hash_object.update(string.encode("utf-8"))
    return hash_object.hexdigest()


def download_file(configuration: Configuration, url: str, destination_dir: Path, show_progress: bool = True):
    """
    Download a file from a URL to a destination directory

    Args:
        configuration (Configuration): The effective application configuration
        url (str): The URL of the file to download
        destination_dir (str): The directory to save the file to
        show_progress (bool, optional): Whether to show a progress bar while downloading. Defaults to True.

    Returns:
        str: The name of the downloaded file
    """

    _check_download_cache_path(configuration)

    url_hash = _get_hash_from_string(url)
    filename_info_path = join(configuration.download_cache_path, f"{url_hash}.filename")

    # The cached file doesn't exist. We must download it.
    if configuration.force_download or not exists(filename_info_path):
        logger.debug("Url not found in download cache.")

        parsed_url = urlparse(url)
        file_name = basename(parsed_url.path)
        destination_base_path = join(configuration.download_cache_path, url_hash)

        if not exists(destination_base_path):
            makedirs(destination_base_path)

        destination_path = join(destination_base_path, file_name)

        urllib.request.urlretrieve(url, destination_path, reporthook=lambda block_num, block_size, total_size: (
            show_progress_bar(block_num * block_size, total_size) if show_progress else None))

        # Hack; the reporthook doesn't report the final block, so we need to print the final progress
        if show_progress:
            show_progress_bar(getsize(destination_path), getsize(destination_path))

        copy(destination_path, destination_dir)

        with open(filename_info_path, 'w') as file:
            file.writelines(file_name)

        return

    with open(filename_info_path, 'r') as file:
        filename = file.readline()

    logger.info(f"Url {url} found in download cache.")
    copy(join(configuration.download_cache_path, url_hash, filename), join(destination_dir, filename))
