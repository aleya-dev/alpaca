from hashlib import sha256
from pathlib import Path

from alpaca.common.logging import logger

_file_info_file_name = ".file_info"

_file_ignore_list = [
    _file_info_file_name,
    ".hash",
    ".package_info"
]


class FileInfo:
    def __init__(self, permissions: str, sha256_hash: str, size: int, name: str):
        self.permissions = permissions
        self.sha256_hash = sha256_hash
        self.size = size
        self.name = name

    def __str__(self):
        return f"{self.permissions} {self.sha256_hash} {self.size} {self.name}"


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


def read_file_info_from_string(file_info_string: str) -> list[FileInfo]:
    """
    Read file info from a string and return a list of FileInfo objects.

    Args:
        file_info_string (str): The string containing file info.

    Returns:
        list[FileInfo]: A list of FileInfo objects.
    """
    file_info_list = []
    lines = file_info_string.strip().splitlines()

    for line in lines:
        parts = line.split()
        if len(parts) != 4:
            raise ValueError(f"Invalid file info line: '{line}'")

        permissions, sha256_hash, size, name = parts
        file_info_list.append(FileInfo(permissions, sha256_hash, int(size), name))

    return file_info_list


def get_total_bytes(file_info_list: list[FileInfo]) -> int:
    """
    Calculate the total size of all files in the file info list.

    Args:
        file_info_list (list[FileInfo]): The list of FileInfo objects.

    Returns:
        int: The total size of all files.
    """
    return sum(file_info.size for file_info in file_info_list)
