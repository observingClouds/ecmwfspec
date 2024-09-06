[![CI](https://github.com/observingClouds/ecmwfspec/workflows/Tests/badge.svg?branch=main)](https://github.com/observingClouds/ecmwfspec/actions?query=workflow%3ATests)
[![Linter](https://github.com/observingClouds/ecmwfspec/workflows/Linter/badge.svg?branch=main)](https://github.com/observingClouds/ecmwfspec/actions?query=workflow%3ALinter)

# ecmwfspec

This is work in progress! This unofficial repository aims to provide an fsspec driver for the [ECMWF File Storage System](https://confluence.ecmwf.int/display/UDOC/ECFS+user+documentation)

Pull requests are welcomed!

```python
import fsspec

with fsspec.open("ec:///ec/res4/scratch/user/file", "r") as f:
    print(f.read())
```
### Loading datasets

```python

import fsspec
import xarray as xr

url = fsspec.open("ec:////arch/project/file.grib").open()
ds = xr.open_dataset(url, engine='cfgrib')  # does not work until https://github.com/ecmwf/cfgrib/issues/326 is solved
```

```
import gribscan
import json
import xarray as xr

file_to_scan = "ec:///path/to/some/grib/file/forecast+0038.grib2"
index_file = "index.json"
reference_file = "reference.json"

gribscan.write_index(gribfile=file_to_scan, idxfile=index_file)  # required currently patch https://github.com/gribscan/gribscan/commit/7a5e595759f48e3118964091358f1b2e9eb32b37 to work with fsspec paths
magician = gribscan.magician.HarmonieMagician()  # use magician fitting the grib file
refs = gribscan.grib_magic(
                        filenames=[index_file],
                        magician=magician,
                        global_prefix="",
                    )


with open(reference_file, "w") as outfile:
    json.dump(refs["heightAboveGround"], outfile)
ds = xr.open_zarr(f"reference::{reference_file}")
ds.u.max()  # with the help of ecmwfspec the data is now fetched if it is not locally cached
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
`EC_CACHE` and accessed directly from there.
