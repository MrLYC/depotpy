"""Filesystem abstraction for optional fsspec integration.

Provides a Protocol-based filesystem interface that is structurally compatible
with fsspec's AbstractFileSystem. Users can pass any fsspec filesystem directly
without depotpy depending on fsspec at runtime.

Usage with local files (default, no extra dependencies):
    from depotpy.fs import LocalFileSystem
    fs = LocalFileSystem()

Usage with fsspec (requires: pip install depotpy[fsspec]):
    import fsspec
    fs = fsspec.filesystem("s3")
    # fs satisfies the FileSystem protocol, pass it directly
"""

from __future__ import annotations

import builtins
import shutil
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import IO, Any, Iterator, Protocol, runtime_checkable


@runtime_checkable
class FileSystem(Protocol):
    """Minimal filesystem interface compatible with fsspec.AbstractFileSystem.

    Any object implementing these methods can be used as a filesystem backend.
    fsspec filesystems satisfy this protocol out of the box.
    """

    def open(self, path: str, mode: str = "rb", **kwargs: Any) -> IO[Any]:
        """Open a file and return a file-like object."""
        ...

    def exists(self, path: str, **kwargs: Any) -> bool:
        """Check if a path exists."""
        ...

    def makedirs(self, path: str, exist_ok: bool = False) -> None:
        """Create directories recursively."""
        ...

    def info(self, path: str, **kwargs: Any) -> dict[str, Any]:
        """Return metadata dict with at least 'size' and 'type' keys."""
        ...

    def ls(self, path: str, detail: bool = False, **kwargs: Any) -> list[Any]:
        """List directory contents. Returns paths (detail=False) or info dicts."""
        ...

    def put(self, lpath: str, rpath: str, **kwargs: Any) -> None:
        """Upload/copy a local file to the filesystem."""
        ...

    def get(self, rpath: str, lpath: str, **kwargs: Any) -> None:
        """Download/copy a file from the filesystem to a local path."""
        ...


class LocalFileSystem:
    """Default local filesystem implementation using pathlib and stdlib.

    This is the zero-dependency fallback used when no filesystem is specified.
    """

    def open(self, path: str, mode: str = "rb", **kwargs: Any) -> IO[Any]:
        """Open a local file."""
        return builtins.open(path, mode, **kwargs)

    def exists(self, path: str, **kwargs: Any) -> bool:
        """Check if a local path exists."""
        return Path(path).exists()

    def makedirs(self, path: str, exist_ok: bool = False) -> None:
        """Create local directories recursively."""
        Path(path).mkdir(parents=True, exist_ok=exist_ok)

    def info(self, path: str, **kwargs: Any) -> dict[str, Any]:
        """Return metadata for a local path."""
        p = Path(path)
        stat = p.stat()
        return {
            "name": str(p),
            "size": stat.st_size,
            "type": "directory" if p.is_dir() else "file",
        }

    def ls(self, path: str, detail: bool = False, **kwargs: Any) -> list[Any]:
        """List local directory contents."""
        p = Path(path)
        if detail:
            return [self.info(str(child)) for child in sorted(p.iterdir())]
        return [str(child) for child in sorted(p.iterdir())]

    def put(self, lpath: str, rpath: str, **kwargs: Any) -> None:
        """Copy a local file to another local path."""
        Path(rpath).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(lpath, rpath)

    def get(self, rpath: str, lpath: str, **kwargs: Any) -> None:
        """Copy a local file to another local path."""
        Path(lpath).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(rpath, lpath)


def is_local(fs: FileSystem) -> bool:
    """Check if a filesystem is effectively local (no network transfer needed)."""
    return isinstance(fs, LocalFileSystem)


def filesystem_from_url(url: str) -> tuple[FileSystem, str]:
    """Parse a URL and return (filesystem, path) using fsspec.

    Args:
        url: A URL like "s3://bucket/path" or "gcs://bucket/path".

    Returns:
        Tuple of (filesystem object, path string).

    Raises:
        ImportError: If fsspec is not installed.
    """
    try:
        import fsspec  # type: ignore[import-untyped]
    except ImportError:
        raise ImportError(
            "fsspec is required for remote filesystem support. "
            "Install it with: pip install depotpy[fsspec]"
        ) from None

    fs, path = fsspec.core.url_to_fs(url)
    return fs, path


@contextmanager
def local_copy(
    fs: FileSystem, remote_path: str, suffix: str = ""
) -> Iterator[Path]:
    """Download a remote file to a local temp file, yield the local Path.

    The temp file is automatically cleaned up when the context exits.

    Args:
        fs: Filesystem to download from.
        remote_path: Path on the remote filesystem.
        suffix: File suffix for the temp file (e.g. ".tar.gz").

    Yields:
        Path to the local temporary copy.
    """
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        local_path = tmp.name
    try:
        fs.get(remote_path, local_path)
        yield Path(local_path)
    finally:
        Path(local_path).unlink(missing_ok=True)
