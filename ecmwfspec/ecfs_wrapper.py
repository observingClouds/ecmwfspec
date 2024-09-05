"""
Wrapper of ECFS file system commands
"""

import os
import subprocess
import logging

logger = logging.getLogger(__name__)

def ls(path, detail=False, allfiles=False, recursive=False, directory=False):
    """
    List files in a directory
    """
    command = ["els", path]
    columns = ['path']

    if detail:
        command.append("-l")
        columns = ['permissions', 'links', 'owner', 'group', 'size', 'month', 'day', 'time', 'path']
    
    if allfiles:
        command.append("-a")
    
    if directory:
        command.append("-d")

    if recursive:
        logger.warning("Recursive option should be avoided on very large ECFS directory tress because of timeout issues.")
        command.append("-R")

    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    logger.debug(result.stdout)

    if result.stderr is not None:
        logger.error(result.stderr)
        raise Exception("Error running command: {}".format(command))

    files = result.stdout.split("\n")
    files = [f for f in files if f != ""]

    if detail:
        files = [f.split() for f in files]

    
    df = pd.DataFrame(files, columns=columns)

    return df

def cp(src, dst):
    """
    Copy a file from src to dst
    """
    command = ["ecp", src, dst]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    logger.debug(result.stdout)

    if result.stderr is not None:
        logger.error(result.stderr)
        raise Exception("Error running command: {}".format(command))

    return result.stdout