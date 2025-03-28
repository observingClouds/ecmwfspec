"""Pytest definitions to run the unittests."""

from __future__ import annotations

import builtins
import os
import shutil
from pathlib import Path
from subprocess import PIPE, run
from tempfile import TemporaryDirectory
from typing import Generator, Union

import mock
import numpy as np
import pandas as pd
import pytest
import xarray as xr


class ECMock:
    """A mock that emulates what pyec is doing."""

    def __init__(self, _cache: dict[int, builtins.list[str]] = {}) -> None:
        self._cache = _cache

    def ec_list(self, inp_path: str) -> str:
        """Mock the ec_list method."""
        res = (
            run(["ls", "-l", inp_path], stdout=PIPE, stderr=PIPE)
            .stdout.decode()
            .split("\n")
        )
        return "\n".join(res[1:] + [res[0]])

    def ls(
        self,
        inp_path: Union[str, Path],
        detail: bool = False,
        allfiles: bool = False,
        recursive: bool = False,
        directory: bool = False,
    ) -> pd.DataFrame:
        """List files in a directory."""
        command = ["ls", inp_path]
        columns = ["path"]

        if recursive:
            command.insert(-1, "-R")
            detail = True

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

        result = run(command, stdout=PIPE, stderr=PIPE, text=True)

        files = result.stdout.split("\n")
        files = [f for f in files if f != ""]

        if detail and not recursive:
            files_incl_details = []
            current_dir = None
            for line in files:
                if line.startswith("total"):
                    continue
                else:
                    files_incl_details.append(line.split())
            df = pd.DataFrame(files_incl_details, columns=columns)
        elif recursive:
            files_incl_details = []
            current_dir = None
            for line in files:
                if line.startswith("/"):
                    current_dir = line.rstrip(":")
                elif line.startswith("total"):
                    continue
                else:
                    details = line.split()
                    if current_dir and details[0].startswith("l"):
                        details.append(current_dir + "/" + details[-1])
                    elif current_dir:
                        details.append(current_dir + "/" + details[-1])
                    files_incl_details.append(details[0:8] + [details[-1]])
            df = pd.DataFrame(files_incl_details, columns=columns)
        else:
            df = pd.DataFrame(files, columns=columns)

        return df

    def cp(self, inp_path: str, out_path: str) -> None:
        """Mock the ecp method."""
        inp_path = inp_path.replace("ec:", "")
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        _ = (
            run(["cp", inp_path, out_path], stdout=PIPE, stderr=PIPE)
            .stdout.decode()
            .split("\n")
        )
        return

    def search(self, inp_f: builtins.list[str]) -> int | None:
        """Mock ec_search."""
        if not inp_f:
            return None
        hash_value = abs(hash(",".join(inp_f)))
        self._cache[hash_value] = inp_f
        return hash_value

    def ec_gen_file_query(self, inp_files: builtins.list[str]) -> builtins.list[str]:
        """Mock ec_gen_file_qeury."""
        return [f for f in inp_files if Path(f).exists()]

    def ec_retrieve(self, search_id: int, out_dir: str, preserve_path: bool) -> None:
        """Mock ec_retrieve."""
        for inp_file in map(Path, self._cache[search_id]):
            if preserve_path:
                outfile = Path(out_dir) / Path(str(inp_file).strip(inp_file.root))
                outfile.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy(inp_file, outfile)
            else:
                shutil.copy(inp_file, Path(out_dir) / inp_file.name)


class ECTMPMock(ECMock):
    """A mock that emulates what ecfs is doing for temporary directories."""

    def __init__(self, _cache: dict[int, builtins.list[str]] = {}) -> None:
        super().__init__(_cache)

    def cp(self, inp_path: str, out_path: str) -> None:
        """Mock the ecp method."""
        inp_path = inp_path.replace("ectmp:", "TMP")
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        _ = (
            run(["cp", inp_path, out_path], stdout=PIPE, stderr=PIPE)
            .stdout.decode()
            .split("\n")
        )
        return


def create_data(variable_name: str, size: int) -> xr.Dataset:
    """Create a xarray dataset."""
    coords: dict[str, np.ndarray] = {}
    coords["x"] = np.linspace(-10, -5, size)
    coords["y"] = np.linspace(120, 125, size)
    lat, lon = np.meshgrid(coords["y"], coords["x"])
    lon_vec = xr.DataArray(lon, name="Lg", coords=coords, dims=("y", "x"))
    lat_vec = xr.DataArray(lat, name="Lt", coords=coords, dims=("y", "x"))
    coords["time"] = np.array(
        [
            np.datetime64("2020-01-01T00:00").astype("datetime64[ns]"),
            np.datetime64("2020-01-01T12:00").astype("datetime64[ns]"),
            np.datetime64("2020-01-02T00:00").astype("datetime64[ns]"),
            np.datetime64("2020-01-02T12:00").astype("datetime64[ns]"),
        ]
    )
    dims = (4, size, size)
    data_array = np.empty(dims)
    for time in range(dims[0]):
        data_array[time] = np.zeros((size, size))
    dset = xr.DataArray(
        data_array,
        dims=("time", "y", "x"),
        coords=coords,
        name=variable_name,
    )
    data_array = np.zeros(dims)
    return xr.Dataset({variable_name: dset, "Lt": lon_vec, "Lg": lat_vec}).set_coords(
        list(coords.keys())
    )


@pytest.fixture(scope="session")
def patch_dir() -> Generator[Path, None, None]:
    with TemporaryDirectory() as temp_dir:
        with mock.patch("ecmwfspec.core.ecfs", ECMock()):
            yield Path(temp_dir)


@pytest.fixture(scope="session")
def patch_ectmp_dir() -> Generator[Path, None, None]:
    with TemporaryDirectory() as temp_dir:
        with mock.patch("ecmwfspec.core.ecfs", ECTMPMock()):
            yield Path(temp_dir)


@pytest.fixture(scope="session")
def save_dir() -> Generator[Path, None, None]:
    """Create a temporary directory."""
    with TemporaryDirectory() as td:
        yield Path(td)


@pytest.fixture(scope="session")
def data() -> Generator[xr.Dataset, None, None]:
    """Define a simple dataset with a blob in the middle."""
    dset = create_data("precip", 100)
    yield dset


@pytest.fixture(scope="session")
def netcdf_files(
    data: xr.Dataset,
) -> Generator[Path, None, None]:
    """Save data with a blob to file."""

    with TemporaryDirectory() as td:
        for time in (data.time[:2], data.time[2:]):
            time1 = pd.Timestamp(time.values[0]).strftime("%Y%m%d%H%M")
            time2 = pd.Timestamp(time.values[1]).strftime("%Y%m%d%H%M")
            out_file = (
                Path(td)
                / "the_project"
                / "test1"
                / "precip"
                / f"precip_{time1}-{time2}.nc"
            )
            out_file.parent.mkdir(exist_ok=True, parents=True)
            data.sel(time=time).to_netcdf(out_file)
        yield Path(td)


@pytest.fixture(scope="session")
def zarr_file(
    data: xr.Dataset,
) -> Generator[Path, None, None]:
    """Save data with a blob to file."""

    with TemporaryDirectory() as td:
        out_file = Path(td) / "the_project" / "test1" / "precip" / "precip.zarr"
        out_file.parent.mkdir(exist_ok=True, parents=True)
        data.to_zarr(out_file)
        yield Path(td)
