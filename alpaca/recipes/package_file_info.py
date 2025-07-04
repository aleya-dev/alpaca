from hashlib import sha256
from pathlib import Path

from alpaca.common.logging import logger

_file_info_file_name = ".file_info"

_file_ignore_list = [
    _file_info_file_name,
    ".hash",
    ".package_info"
]


def write_file_info(path: Path | str):
    """
    Write a .file_info file to the specified path.

    A fileinfo file is a simple text file that contains the permissions, sha256 hash, the size,
    and the file name of each file in the package directory.

    Args:
        path (Path): The path where the .file_info file will be written.
    """
    path = Path(path)

    if not path.is_dir():
        raise ValueError(f"The specified path '{path}' is not a directory or does not exist.")

    logger.info(f"Writing file info to {path / _file_info_file_name}")

    with open(path / _file_info_file_name, "w") as file_info:
        for file in path.rglob("*"):
            if file.is_file():
                if file.name in _file_ignore_list:
                    continue

                permissions = oct(file.stat().st_mode)[-3:]
                sha256_hash = sha256(file.read_bytes()).hexdigest()
                size = file.stat().st_size
                file_info.write(f"{permissions} {sha256_hash} {size} {file.name}\n")

    logger.info(f"File info written to {path / _file_info_file_name}")
