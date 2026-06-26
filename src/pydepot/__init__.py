"""PyDepot - Build cross-platform offline installation packages for Python projects."""

__version__ = "0.1.0"

from pydepot.commands.inspect import BundleInspector
from pydepot.installer import BundleInstaller
from pydepot.packer import PackBuilder

__all__ = [
    "BundleInspector",
    "BundleInstaller",
    "PackBuilder",
    "__version__",
]
