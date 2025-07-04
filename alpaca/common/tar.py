import tarfile
from os import walk
from os.path import join, relpath
from pathlib import Path

from alpaca.common.logging import logger


def extract_tar(file_path: Path, destination_dir: Path):
    """
    Untar a file to a destination directory

    Args:
        file_path (Path): The path of the tar file to extract
        destination_dir (Path): The directory to extract the tar file to
    """

    logger.verbose(f"Extracting {file_path} to {destination_dir}...")

    with tarfile.open(file_path, "r") as tar:
        tar.extractall(destination_dir)

    logger.verbose(f"File {file_path} extracted to {destination_dir}")


def compress_tar(directory: Path, archive_path: Path):
    """
    Compress a directory to a tar.xz archive

    Args:
        directory (Path): The source directory to archive
        archive_path (Path): The path of the target archive
    """

    logger.verbose(f"Archiving directory {directory} to {archive_path}...")

    files = []
    for root, _, filenames in walk(directory):
        for filename in filenames:
            files.append(join(root, filename))

    with tarfile.open(archive_path, "w:xz") as tar:
        for file in files:
            tar.add(file, arcname=relpath(file, directory))

    logger.verbose(f"Directory {directory} archived to {archive_path}")
