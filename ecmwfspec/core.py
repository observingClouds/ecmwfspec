from __future__ import annotations

import io
import logging
import os
import threading
import time
import warnings
from pathlib import Path
from queue import Queue
from typing import (
    IO,
    Any,
    Dict,
    List,
    Literal,
    Optional,
    Tuple,
    TypedDict,
    Union,
    overload,
)

import pandas as pd
from fsspec.spec import AbstractFileSystem
from upath import UPath

from . import ecfs_wrapper as ecfs

logger = logging.getLogger("ecmwfspec")
logger.setLevel(logging.DEBUG)


MAX_RETRIES = 2
FileQueue: Queue[Tuple[str, str]] = Queue(maxsize=-1)


class FileInfo(TypedDict):
    name: str
    size: Optional[int]
    type: Optional[str]


_retrieval_lock = threading.Lock()


class ECFile(io.IOBase):
    """File handle for files on the hsm archive.

    Parameters
    ----------
    url: str
        Source path of the file that should be retrieved.
    local_file: str
        Destination path of the downloaded file.
    ec_cache: str | Path
        Destination of the temporary storage. This directory is used to
        retrieve data from tape.
    override: bool, default: False
        Override existing files
    touch: bool, default: True
        Update existing files on the temporary storage to prevent them
        from being deleted.
    mode: str, default: rb
        Specify the mode in which the files are opened

        'r'       open for reading (default)
        'b'       binary mode (default)
        't'       text mode
    file_permissions: int, default 0o3777
        Permission when creating directories and files.
    **kwargs:
        Additional keyword arguments passed to the open file descriptor method.

    Example
    -------

    Use fsspec to open data stored on tape, temporary data will be downloaded
    to a central scratch folder:

    ::

        import ffspec
        import xarray as xr

        url = fsspec.open("ec:////arch/bb1203/data.nc",
                          ec_cache="/scratch/b/b12346").open()
        dset = xr.open_dataset(url)
    """

    write_msg: str = "Write mode is not suppored"
    """Error message that is thrown if the files are attempted to be opened in
    any kind of write mode."""

    def __init__(
        self,
        url: str,
        local_file: str,
        ec_cache: Union[str, Path],
        *,
        override: bool = True,
        mode: str = "rb",
        touch: bool = True,
        file_permissions: int = 0o3777,
        delay: int = 2,
        _lock: threading.Lock = _retrieval_lock,
        _file_queue: Queue[Tuple[str, str]] = FileQueue,
        **kwargs: Any,
    ):
        if not set(mode) & set("r"):  # The mode must have a r
            raise NotImplementedError(self.write_msg)
        if "b" not in mode:
            kwargs.setdefault("encoding", "utf-8")
        self._file = str(Path(local_file).expanduser().absolute())
        self._url = str(url)
        self.ec_cache = Path(ec_cache)
        self.touch = touch
        self.file_permissions = file_permissions
        self._order_num = 0
        self._file_obj: Optional[IO[Any]] = None
        self._lock = _lock
        self.kwargs = kwargs
        self.mode = mode
        self.newlines = None
        self.error = "strict"
        self.encoding = kwargs.get("encoding")
        self.write_through = False
        self.delay = delay
        self._file_queue = _file_queue
        print(self._file)
        with _lock:
            if not Path(self._file).exists() or override:
                self._file_queue.put((self._url, str(Path(self._file).parent)))
            elif Path(self._file).exists():
                if self.touch:
                    Path(self._file).touch()
                self._file_obj = open(self._file, mode, **kwargs)

    @property
    def name(self) -> str:
        """Get the file for the ECFile object."""
        if self._file_obj is not None:
            return self._file
        return self._url

    def _retrieve_items(self, retrieve_files: list[tuple[str, str]]) -> None:
        """Get items from the tape archive."""

        retrieval_requests: List[str] = list()
        logger.debug("Retrieving %i items from ECFS", len(retrieve_files))
        for inp_file, _ in retrieve_files:
            retrieval_requests.append(inp_file)
        for file in retrieval_requests:
            logger.debug("Retrieving file: %s", file)
            local_path = self.ec_cache / Path(file.strip("/"))
            ecfs.cp("ec:" + file, str(local_path))
            local_path.chmod(self.file_permissions)

    def _cache_files(self) -> None:
        time.sleep(self.delay)
        with self._lock:
            items = []
            if self._file_queue.qsize() > 0:
                self._file_queue.put(("finish", "finish"))
                for _ in range(self._file_queue.qsize() - 1):
                    items.append(self._file_queue.get())
                    self._file_queue.task_done()
                try:
                    self._retrieve_items(items)
                except Exception as error:
                    _ = [
                        self._file_queue.get() for _ in range(self._file_queue.qsize())
                    ]
                    self._file_queue.task_done()
                    raise error
                _ = self._file_queue.get()
                self._file_queue.task_done()
        self._file_queue.join()
        self._file_obj = open(self._file, self.mode, **self.kwargs)

    def __fspath__(self) -> str:
        if self._file_obj is None:
            self._cache_files()
        return self.name

    def tell(self) -> int:
        if self._file_obj is None:
            self._cache_files()
        return self._file_obj.tell()  # type: ignore

    def seek(self, target: int, whence: int = 0) -> int:
        if self._file_obj is None:
            self._cache_files()
        return self._file_obj.seek(target, whence)  # type: ignore

    def peek(self, size: int = 0) -> bytes:
        if self._file_obj is None:
            self._cache_files()
        return self._file_obj.peek(size)  # type: ignore

    @staticmethod
    def readable() -> Literal[True]:
        """Compatibility method."""
        return True

    @staticmethod
    def writeable() -> Literal[False]:
        """Compatibility method."""
        return False

    @staticmethod
    def seekable() -> Literal[True]:
        """Compatibility method."""
        return True

    def read(self, size: int = -1) -> str:
        """The the content of a file-stream.

        size: int, default: -1
            read at most size characters from the stream, -1 means everything
            is read.
        """
        if self._file_obj is None:
            self._cache_files()
        return self._file_obj.read(size)  # type: ignore

    @staticmethod
    def flush() -> None:
        """Flushing file systems shouldn't work for ro modes."""
        return None

    def writelines(self, *arg: Any) -> None:
        """Compatibility method."""
        raise NotImplementedError(self.write_msg)

    def write(self, *arg: Any) -> None:
        """Writing to tape is not supported."""
        raise NotImplementedError(self.write_msg)

    def close(self) -> None:
        if self._file_obj is not None:
            self._file_obj.close()


class ECFileSystem(AbstractFileSystem):
    """Abstract class for hsm files systems.

    The implementation intracts with the hsm tape storage system, files
    that are accessed are downloaded to a temporary data storage.

    Parameters
    ----------

    ec_cache: str | Path, default: None
        Destination of the temporary storage. This directory is used to
        retrieve data from tape.
    block_size: int, default: None
         Some indication of buffering - this is a value in bytes
    file_permissions: int, default: 0o3777
        Permission when creating directories and files.
    override: bool, default: False
        Override existing files
    touch: bool, default: True
        Update existing files on the temporary storage to prevent them
        from being deleted.
    **storage_options:
        Additional options passed to the AbstractFileSystem class.
    """

    protocol = "ec"
    local_file = True
    sep = "/"

    def __init__(
        self,
        block_size: Optional[int] = None,
        ec_cache: Optional[Union[str, Path]] = None,
        file_permissions: int = 0o3777,
        touch: bool = True,
        delay: int = 2,
        override: bool = False,
        **storage_options: Any,
    ):
        super().__init__(
            block_size=block_size,
            asynchronous=False,
            loop=None,
            **storage_options,
        )
        ec_options = storage_options.get("ec", {})
        ec_cache = (
            ec_options.get("ec_cache", None) or ec_cache or os.environ.get("EC_CACHE")
        )
        if not ec_cache:
            ec_cache = os.environ.get("SCRATCH", None)
            if ec_cache is None:
                raise ValueError("No cache directory specified.")
            else:
                warnings.warn(
                    "Neither the ec_cache argument nor the EC_CACHE environment "
                    "variable is set. Falling back to default "
                    f"{ec_cache}",
                    UserWarning,
                    stacklevel=2,
                )
        self.touch = touch
        self.ec_cache = Path(ec_cache)
        self.override = override
        self.delay = delay
        self.file_permissions = file_permissions
        self.file_listing_cache: pd.DataFrame = pd.DataFrame(
            columns=[
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
        )

    @overload
    def ls(
        self, path: Union[str, Path, UPath], detail: Literal[True], **kwargs: Any
    ) -> List[FileInfo]: ...

    @overload
    def ls(
        self, path: Union[str, Path, UPath], detail: Literal[False], **kwargs: Any
    ) -> List[str]: ...

    def ls(
        self,
        path: Union[str, Path, UPath],
        detail: bool = True,
        recursive: bool = False,
        **kwargs: Any,
    ) -> Union[List[FileInfo], List[str]]:
        """List objects at path.

        This includes sub directories and files at that location.

        Parameters
        ----------
        path: str | pathlib.Path | UPath
            Path of the file object that is listed.
        detail: bool, default: True
            if True, gives a list of dictionaries, where each is the same as
            the result of ``info(path)``. If False, gives a list of paths
            (str).


        Returns
        -------
        list : List of strings if detail is False, or list of directory
               information dicts if detail is True.
        """
        if isinstance(path, UPath):
            path = path
        elif isinstance(path, str):
            path = UPath(path)
        elif isinstance(path, Path):
            path = UPath(str(path))
        else:
            raise TypeError(f"Path type {type(path)} not supported.")

        if self.protocol == "ectmp":
            url = "ectmp:/" / path.relative_to(path.anchor)
        else:
            url = path

        if recursive:
            filelist = self.file_listing_cache.loc[
                self.file_listing_cache["path"].str.startswith(path.path)
            ]
        else:
            filelist = self.file_listing_cache.loc[
                self.file_listing_cache["path"] == str(path)
            ]
        if filelist.empty:
            filelist = ecfs.ls(str(url), detail=detail, recursive=recursive)
            if self.protocol == "ectmp":
                filelist.path = filelist.path.str.replace("/TMP", "")
            if (
                recursive
            ):  # only in case of recursive to ensure subdirectories are added to cache
                self.file_listing_cache = pd.concat(
                    [self.file_listing_cache, filelist], ignore_index=True
                )
        # Drop summary line of detailed listing
        # if detail:
        #     filelist = filelist[filelist.permissions != "total"]
        detail_list: List[FileInfo] = []
        types = {"d": "directory", "-": "file", "o": "file"}  # o is undocumented
        detail_list = [
            {
                "name": str(path / file_entry.path),
                "size": file_entry.size,
                "type": types[file_entry.permissions[0]] if detail else None,
            }
            for _, file_entry in filelist.iterrows()
        ]
        if detail:
            return detail_list
        else:
            return [d["name"] for d in detail_list]

    def exists(self, path: str | Path, **kwargs: Any) -> bool:
        """Is there a file at the given path."""
        try:
            self.ls(path, **kwargs)
            return True
        except:  # noqa: E722
            # any exception allowed bar FileNotFoundError?
            return False

    def owner(self, path: str | Path, **kwargs: Any) -> str:
        details = ecfs.ls(str(path), detail=True, recursive=False)
        return details["owner"].values.item(0)

    def _open(
        self,
        path: str | Path,
        mode: str = "rb",
        block_size: Optional[int] = None,
        autocommit: bool = True,
        cache_options: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> ECFile:
        path = Path(self._strip_protocol(path))
        local_path = Path(os.path.join(self.ec_cache, path.relative_to(path.anchor)))
        return ECFile(
            str(path),
            str(local_path),
            self.ec_cache,
            mode=mode,
            override=self.override,
            touch=self.touch,
            delay=self.delay,
            encoding=kwargs.get("encoding"),
            file_permissions=self.file_permissions,
        )


class ECTmpFileSystem(ECFileSystem):
    protocol = "ectmp"
    local_file = True
    sep = "/"

    def __init__(
        self,
        block_size: Optional[int] = None,
        ec_cache: Optional[Union[str, Path]] = None,
        file_permissions: int = 0o3777,
        touch: bool = True,
        delay: int = 2,
        override: bool = False,
        **storage_options: Any,
    ) -> None:
        super().__init__(
            block_size=block_size,
            ec_cache=ec_cache,
            file_permissions=file_permissions,
            touch=touch,
            delay=delay,
            override=override,
            **storage_options,
        )

    def _open(
        self,
        path: str | Path,
        mode: str = "rb",
        block_size: Optional[int] = None,
        autocommit: bool = True,
        cache_options: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> ECFile:
        if isinstance(path, Path):
            path = "/TMP" / Path(self._strip_protocol(path)).relative_to(path.anchor)
        elif isinstance(path, str):
            path = Path("/TMP/" + path)
        local_path = Path(os.path.join(self.ec_cache, path.relative_to(path.anchor)))
        return ECFile(
            str(path),
            str(local_path),
            self.ec_cache,
            mode=mode,
            override=self.override,
            touch=self.touch,
            delay=self.delay,
            encoding=kwargs.get("encoding"),
            file_permissions=self.file_permissions,
        )


class ECFSPath(UPath):
    @property
    def path(self) -> str:
        path = "/".join(self.parts)

        if not path.startswith("/"):
            path = "/" + path

        return path

    def owner(self) -> str:
        owner = self.fs.owner(self)
        return owner


class ECFSTmpPath(UPath):
    @property
    def path(self) -> str:
        path = "/".join(self.parts)

        if not path.startswith("/TMP/"):
            path = "/TMP/" + path

        # self.protocol = "ec"

        return path

    def owner(self) -> str:
        owner = self.fs.owner(self)
        return owner
