# Changelog

## unreleased
- Fix pre-commit docformatter hook [#19](https://github.com/observingClouds/ecmwfspec/pull/19)
- Add caching of file listings for faster look-ups [#18](https://github.com/observingClouds/ecmwfspec/pull/18)
- Add support for recursive file listings (`ls -R`) [#18](https://github.com/observingClouds/ecmwfspec/pull/18)
- Fix `isdir()` function call [#15](https://github.com/observingClouds/ecmwfspec/pull/15)
- Add UPath support for ec-protocol [#15](https://github.com/observingClouds/ecmwfspec/pull/15)
- Raise specific errors when `ls` fails due to PermissionError or FileNotFoundError [#15](https://github.com/observingClouds/ecmwfspec/pull/15)

## 0.0.2
- Add support for `ectmp` file paths [#2](https://github.com/observingClouds/ecmwfspec/issues/2)
- Fix file listing when using additional flags [#9](https://github.com/observingClouds/ecmwfspec/issues/9)
- Fix incorrect caching if cache directory is given as absolute path [#10](https://github.com/observingClouds/ecmwfspec/issues/10)
- Fix some warnings in test suite. [#11](https://github.com/observingClouds/ecmwfspec/issues/11)
- Fix ec_cache for `ectmp` file protocol [#12](https://github.com/observingClouds/ecmwfspec/issues/12)

## 0.0.1
- Initial release
