from fsspec import register_implementation

from .core import ECFileSystem, ECTmpFileSystem, logger

register_implementation(ECFileSystem.protocol, ECFileSystem)
register_implementation(ECTmpFileSystem.protocol, ECTmpFileSystem)

__all__ = ["ECFileSystem", "ECTmpFileSystem", "logger"]
