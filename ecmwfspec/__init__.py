from fsspec import register_implementation

from . import _version
from .core import ECFileSystem, logger

__version__ = _version.get_versions()["version"]

register_implementation(ECFileSystem.protocol, ECFileSystem)

__all__ = ["__version__", "ECFileSystem", "logger"]
