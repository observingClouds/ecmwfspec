"""Wrapper of ECFS file system commands."""

import logging
import subprocess
from pathlib import Path
from typing import Union

import pandas as pd

logger = logging.getLogger(__name__)


def ls(
    path: Union[str, Path],
    detail: bool = False,
    allfiles: bool = False,
    recursive: bool = False,
    directory: bool = False,
) -> pd.DataFrame:
    """List files in a directory."""
    command = ["els", str(path).replace("ec:", "ec:/")]
    columns = ["path"]

    if detail:
        command.insert(-1, "-l")
        columns = [
            "permissions",
            "links",
            "owner",
            "group",
            "size",
            "month",
            "day",
            "time",
            "path",
        ]

    if allfiles:
        command.insert(-1, "-a")

    if directory:
        command.insert(-1, "-d")

    if recursive:
        logger.warning(
            "Recursive option should be avoided on very large ECFS directory tress because of timeout issues."
        )
        command.insert(-1, "-R")

    result = subprocess.run(
        command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
    )
    logger.debug(result.stdout)

    if result.stderr is not None:
        logger.error(result.stderr)
        raise Exception("Error running command: {}".format(command))

    files = result.stdout.split("\n")  # type: ignore
    files = [f for f in files if f != ""]

    if detail:
        files = [f.split() for f in files]

    df = pd.DataFrame(files, columns=columns)

    return df


def cp(src: Union[str, Path], dst: Union[str, Path]) -> None:
    """Copy a file from src to dst."""
    command = ["ecp", str(src).replace("ec:", "ec:/"), dst]
    result = subprocess.check_output(command, text=True)
    logger.debug(result)

    if result != "":
        logger.error(result)
        raise Exception("Error running command: {}".format(command))

    return
