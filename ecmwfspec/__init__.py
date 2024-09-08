from fsspec import register_implementation

from .core import ECFileSystem, logger

register_implementation(ECFileSystem.protocol, ECFileSystem)

__all__ = ["ECFileSystem", "logger"]
