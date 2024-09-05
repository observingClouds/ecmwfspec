[![CI](https://github.com/observingClouds/ecmwfspec/workflows/Tests/badge.svg?branch=main)](https://github.com/observingClouds/ecmwfspec/actions?query=workflow%3ATests)
[![Linter](https://github.com/observingClouds/ecmwfspec/workflows/Linter/badge.svg?branch=main)](https://github.com/observingClouds/ecmwfspec/actions?query=workflow%3ALinter)

# ecmwfspec

This is work in progress! This repository showcases how the tape archive can be integrated into the scientific workflow.

Pull requests are welcomed!

```python
import fsspec

with fsspec.open("ec:///arch/project/user/file", "r") as f:
    print(f.read())
```
### Loading datasets

```python

import ffspec
import xarray as xr

url = fsspec.open("ec:////arch/project/file.nc", ec_cache="/scratch/b/b12346").open()
dset = xr.open_dataset(url)
```


## Usage in combination with preffs
### Installation of additional requirements
```console
mamba env create
mamba activate ecmwfspec
pip install .[preffs]
```

Open parquet referenced zarr-file
```python
import xarray as xr
ds = xr.open_zarr(f"preffs::/path/to/preffs/data.preffs",
                storage_options={"preffs":{"prefix":"ec:///arch/<project>/<user>/ec/archive/prefix/"}
```

Now only those files are retrieved from tape which are needed for any requested
dataset operation. In the beginning only the file containing the metadata
(e.g. .zattrs, .zmetadata) and coordinates are requested (e.g. time). After the
files have been retrieved once, they are saved at the path given in
`ec_CACHE` and accessed directly from there.
