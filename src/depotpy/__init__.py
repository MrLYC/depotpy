"""DepotPy - Build cross-platform offline installation packages for Python projects."""

__version__ = "1.0.0"

from depotpy.commands.inspect import BundleInspector
from depotpy.fs import FileSystem, LocalFileSystem, filesystem_from_url
from depotpy.installer import BundleInstaller
from depotpy.packer import PackBuilder

__all__ = [
    "BundleInspector",
    "BundleInstaller",
    "FileSystem",
    "LocalFileSystem",
    "PackBuilder",
    "__version__",
    "filesystem_from_url",
]
