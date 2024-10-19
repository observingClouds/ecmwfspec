"""Testing opening of datasets."""

import importlib
import os
import shutil
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

import fsspec
import pytest
import xarray as xr
from xarray.testing import assert_identical

import ecmwfspec
from ecmwfspec import xr_accessor  # noqa: F401


def test_protocols() -> None:
    """Test that fsspec protocols are registered."""
    protocols = fsspec.available_protocols()
    assert "ec" in protocols, f"ec not found in {protocols}"
    assert "ectmp" in protocols, f"ectmp not found in {protocols}"


def test_xr_accessor(patch_dir: Path, zarr_file: Path) -> None:
    """Test staging."""
    zarr_file1 = [*zarr_file.rglob("*.zarr")][0]
    urls = [f"ec://{zarr_file1}"]

    dataset = xr.open_dataset(
        urls[0],
        engine="zarr",
        chunks={"time": 2, "x": 100, "y": 100},
        backend_kwargs={"storage_options": {"ec": {"ec_cache": patch_dir}}},
    )
    dataset_original = xr.open_dataset(zarr_file1, engine="zarr")
    path_to_precip_chunks = os.path.join(
        patch_dir, urls[0].replace("ec:///", ""), "precip"
    )
    assert dataset["precip"]._in_memory is False, "dataset has been loaded into memory"
    assert (
        os.path.exists(path_to_precip_chunks) is False
    ), "zarr directory exists, though chunks should not exist yet"
    dataset["precip"].ecfs.stage()
    assert dataset["precip"]._in_memory is False, "dataset has been loaded into memory"
    assert os.path.exists(path_to_precip_chunks), "chunks were not requested"
    files = os.listdir(path_to_precip_chunks)
    assert len(files) == 2, "chunks files are missing"
    dataset_original.load()
    shutil.rmtree(zarr_file1)
    dataset["precip"].load()
    assert_identical(dataset.precip, dataset_original.precip)


def test_reading_dataset(patch_dir: Path, netcdf_files: Path) -> None:
    """Test reading datafiles with ecmwfspec."""
    import fsspec

    urls = [
        fsspec.open(f"ec://{f}", ec_cache=patch_dir, override=True).open()
        for f in netcdf_files.rglob("*.nc")
    ]
    dataset1 = xr.open_mfdataset(list(netcdf_files.rglob("*.nc")), combine="by_coords")
    dataset2 = xr.open_mfdataset(urls, combine="by_coords")
    assert dataset1 == dataset2


@mock.patch.dict(os.environ, {}, clear=True)
def test_errors(patch_dir: Path) -> None:
    """Check if ec specs warns the users if the cache wasn't set and fallback
    not available."""
    importlib.reload(ecmwfspec)
    importlib.reload(fsspec)

    with pytest.raises(ValueError):
        fsspec.open("ec:///foo/bar.txt", mode="rt").open()

    ecmwfspec.core.FileQueue.queue.clear()  # TODO: empty queue automatically


@mock.patch.dict(os.environ, {"SCRATCH": str(TemporaryDirectory())}, clear=True)
def test_warnings(patch_dir: Path) -> None:
    """Check if ec specs warns the users if the cache wasn't set and fallback
    not available."""
    importlib.reload(fsspec)

    with pytest.warns(UserWarning):
        fsspec.open("ec:///foo/bar.txt", mode="rt").open()

    ecmwfspec.core.FileQueue.queue.clear()  # TODO: empty queue automatically


def test_reading_nonexisting_dataset(patch_dir: Path, netcdf_files: Path) -> None:
    """Test read-failure on non-existing files."""
    import fsspec

    non_existing_urls = fsspec.open(
        "ec:///foo/bar.nc",
        ec_cache=patch_dir,
        mode="rt",
    ).open()
    with pytest.raises(FileNotFoundError):
        non_existing_urls.read()


def test_text_mode(patch_dir: Path) -> None:
    """Test opening the files in text mode."""
    import fsspec

    with TemporaryDirectory() as temp_dir:
        inp_file = Path(temp_dir) / "foo.txt"
        write_file = patch_dir.joinpath(*inp_file.parts[1:])
        write_file.parent.mkdir(exist_ok=True, parents=True)
        print(write_file)
        with write_file.open("w") as f_obj:
            f_obj.write("foo")
        url = fsspec.open(
            f"ec:///{inp_file}",
            ec_cache=patch_dir,
            override=False,
            mode="rt",
        ).open()
    assert Path(url.name) == write_file
    assert url.tell() == 0
    assert url.read() == "foo"


def test_ro_mode(patch_dir: Path) -> None:
    """Check if ec specs is ro."""
    import fsspec

    with pytest.raises(NotImplementedError):
        fsspec.open("ec:///foo/bar.nc", mode="w").open()

    url = fsspec.open("ec:///foo/bar.txt", ec_cache="foo").open()

    with pytest.raises(NotImplementedError):
        url.writelines()

    with pytest.raises(NotImplementedError):
        url.write()

    assert url.writable() is False


def test_ectmp(patch_ectmp_dir: Path) -> None:
    """Check if ectmp access works."""
    import fsspec

    with TemporaryDirectory() as temp_dir:
        inp_file = Path(temp_dir) / "foo.txt"
        write_file = (patch_ectmp_dir / "TMP").joinpath(*inp_file.parts[1:])
        write_file.parent.mkdir(exist_ok=True, parents=True)
        print(write_file)
        with write_file.open("w") as f_obj:
            f_obj.write("foo")
        url = fsspec.open(
            f"ectmp:///{inp_file}",
            ec_cache=patch_ectmp_dir,
            override=False,
            mode="rt",
        ).open()
    assert Path(url.name) == write_file
    assert url.tell() == 0
    assert url.read() == "foo"


def test_ectmp_strpath(patch_ectmp_dir: Path) -> None:
    """Check if ectmp access works."""
    import fsspec

    with TemporaryDirectory() as temp_dir:
        inp_file = Path(temp_dir) / "foo.txt"
        write_file = (patch_ectmp_dir / "TMP").joinpath(*inp_file.parts[1:])
        write_file.parent.mkdir(exist_ok=True, parents=True)
        print(write_file)
        with write_file.open("w") as f_obj:
            f_obj.write("foo")
        url = fsspec.open(
            f"ectmp:///{inp_file}",
            ec_cache=str(patch_ectmp_dir),
            override=False,
            mode="rt",
        ).open()
    assert Path(url.name) == write_file
    assert url.tell() == 0
    assert url.read() == "foo"


def test_list_files(patch_dir: Path, netcdf_files: Path) -> None:
    """Test listing the files."""
    import fsspec

    folder_w_netcdffiles = netcdf_files / "the_project" / "test1" / "precip"
    files = list(folder_w_netcdffiles.iterdir())
    ec = fsspec.filesystem("ec", ec_cache=patch_dir)
    res = ec.ls(folder_w_netcdffiles, detail=False)
    assert len(files) == len(res)
    res = ec.ls(folder_w_netcdffiles, detail=True)
    for info in res:
        assert isinstance(info, dict)
        assert "name" in info
        assert "type" in info
        assert "size" in info
        assert info["size"] == 9
