"""DepotPy - Build cross-platform offline installation packages for Python projects."""

__version__ = "0.3.0"

from depotpy.commands.inspect import BundleInspector
from depotpy.installer import BundleInstaller
from depotpy.packer import PackBuilder

__all__ = [
    "BundleInspector",
    "BundleInstaller",
    "PackBuilder",
    "__version__",
]
