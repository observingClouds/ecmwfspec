"""Wrapper of ECFS file system commands."""

import logging
import subprocess
from pathlib import Path
from typing import Optional, Union

import pandas as pd
from upath import UPath

logger = logging.getLogger(__name__)


def ls(
    path: Union[str, Path, UPath],
    detail: bool = False,
    allfiles: bool = False,
    recursive: bool = False,
    directory: bool = False,
    order: Optional[str] = None,
) -> pd.DataFrame:
    """List files in a directory."""
    if isinstance(path, Path):
        path = str(path)
    elif isinstance(path, str):
        path = path
    elif isinstance(path, UPath):
        path = path.path

    if order == 'tape':
        if not detail:
            raise ValueError("tape ordering requires detailed listing")
        if recursive:
            raise NotImplementedError("tape ordering not supported for recursive listing")
        extended = True
    else:
        extended = False

    command = ["els", path.replace("ec:", "ec:/").replace("ectmp:", "ectmp:/")]
    columns = ["path"]

    if recursive:
        logger.warning(
            "Recursive option should be avoided on very large ECFS directory trees because of timeout issues."
        )
        command.insert(-1, "-R")
        detail = True

    if detail:
        command.insert(-1, "-l")
        if extended:
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
                "offline",
                "backup",
                "staged",
                "safety",
                "volser",
                "offset",
                "fileno",
            ]
        else:
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

    if extended:
        command.insert(-1, "-E")

    if allfiles:
        command.insert(-1, "-a")

    if directory:
        command.insert(-1, "-d")

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

    if detail and not recursive:
        files = [f.split() for f in result_lines]
    elif recursive:
        files = []
        current_dir = path.replace("ec:", "").replace("ectmp:", "")
        for line in result_lines:
            if line.startswith("/"):
                current_dir = line.rstrip(":")
            elif line.startswith("total"):
                continue
            elif line.endswith(" .."):
                continue
            else:
                details = line.split()
                if current_dir:
                    details.append(current_dir + "/" + details[-1])
                files.append(details[0:8] + [details[-1]])
    else:
        files = result_lines  # type: ignore

    df = pd.DataFrame(files, columns=columns)

    if extended:
        df['tape'] = df['volser'].str.extract(r'volser=(\w+)')
        df = df.sort_values('tape')

    return df


def cp(src: Union[str, Path], dst: Union[str, Path]) -> None:
    """Copy a file from src to dst."""
    command = [
        "ecp",
        str(src).replace("ec:", "ec:/").replace("ectmp:", "ectmp:/"),
        dst,
    ]
    result = subprocess.check_output(command, text=True)
    logger.debug(result)

    if result != "":
        logger.error(result)
        raise Exception("Error running command: {}".format(command))

    return
