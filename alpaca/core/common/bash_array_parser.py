import shlex
from typing import List

from alpaca.core.alpaca_error import AlpacaError


class BashArrayParseError(AlpacaError):
    pass


def parse_bash_array(output: str) -> List[str]:
    trimmed = output.strip()
    if not trimmed.startswith("(") or not trimmed.endswith(")"):
        raise BashArrayParseError("Invalid Bash array format")

    inner = trimmed[1:-1]
    # shlex splits like the shell, respecting quotes and escapes
    lexer = shlex.shlex(inner, posix=True)
    lexer.whitespace_split = True
    lexer.whitespace = " ,"
    lexer.commenters = ""

    return list(lexer)
