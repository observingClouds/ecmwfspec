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
        command, check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )
    logger.debug(result.stdout)
    if result.returncode != 0:
        logger.debug(result.stderr)
        if "Permission denied" in result.stderr:
            raise PermissionError(result.stderr)
        elif "File does not exist" in result.stderr:
            raise FileNotFoundError(result.stderr)
        else:
            raise Exception(result.stderr)

    result_lines = result.stdout.split("\n")
    result_lines = [f for f in result_lines if f != ""]

    if detail:
        files = [f.split() for f in result_lines]
    else:
        files = result_lines  # type: ignore

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
