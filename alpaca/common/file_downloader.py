from os.path import basename, join, getsize
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import urlretrieve
from alpaca.common.progress_bar import show_progress_bar


def download_file(url: str, destination_dir: Path, show_progress: bool = True):
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
    file_name = basename(parsed_url.path)
    destination_path = join(destination_dir, file_name)

    urlretrieve(url, destination_path, reporthook=lambda block_num, block_size, total_size: (
        show_progress_bar(block_num * block_size, total_size) if show_progress else None))

    # Hack; the reporthook doesn't report the final block, so we need to print the final progress
    if show_progress:
        show_progress_bar(getsize(destination_path), getsize(destination_path))
