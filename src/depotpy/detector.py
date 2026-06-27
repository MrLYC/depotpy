"""Dependency manager detection and project info extraction."""

from __future__ import annotations

import configparser
import json
import logging
import shutil
from pathlib import Path
from typing import Any

from depotpy.fs import FileSystem, LocalFileSystem
from depotpy.models import DependencyManager, ProjectInfo

try:
    import tomllib
except ImportError:
    import tomli as tomllib  # type: ignore[no-redef,import-not-found]

logger = logging.getLogger(__name__)

_DEFAULT_FS = LocalFileSystem()


def _read_toml(path: Path, fs: FileSystem | None = None) -> dict[str, Any] | None:
    """Read a TOML file and return its contents as a dict.

    Returns None if the file cannot be parsed.
    """
    try:
        with (fs or _DEFAULT_FS).open(str(path), "rb") as f:
            return tomllib.load(f)
    except Exception as e:
        logger.warning("Failed to parse TOML file %s: %s", path, e)
        return None


def _fs_exists(path: Path, fs: FileSystem | None = None) -> bool:
    """Check if a path exists, using the filesystem if provided."""
    if fs is not None:
        return fs.exists(str(path))
    return path.exists()


def _fs_read_text(path: Path, fs: FileSystem | None = None) -> str:
    """Read a text file, using the filesystem if provided."""
    with (fs or _DEFAULT_FS).open(str(path), "r") as f:
        content: str = f.read()
        return content


def _detect_manager(
    project_path: Path, fs: FileSystem | None = None
) -> DependencyManager:
    """Detect the dependency manager used by the project.

    Priority: uv > poetry > pdm > pipenv > pip
    """
    pyproject = project_path / "pyproject.toml"

    if _fs_exists(pyproject, fs):
        data = _read_toml(pyproject, fs)
        if data is None:
            return DependencyManager.PIP
        tool = data.get("tool", {})

        # uv: check for uv.lock or [tool.uv]
        if _fs_exists(project_path / "uv.lock", fs) or "uv" in tool:
            if shutil.which("uv"):
                return DependencyManager.UV

        # poetry: check for poetry.lock or [tool.poetry]
        if _fs_exists(project_path / "poetry.lock", fs) or "poetry" in tool:
            if shutil.which("poetry"):
                return DependencyManager.POETRY

        # pdm: check for pdm.lock or [tool.pdm]
        if _fs_exists(project_path / "pdm.lock", fs) or "pdm" in tool:
            if shutil.which("pdm"):
                return DependencyManager.PDM

    # pipenv: check for Pipfile or Pipfile.lock
    if _fs_exists(project_path / "Pipfile", fs) or _fs_exists(
        project_path / "Pipfile.lock", fs
    ):
        if shutil.which("pipenv"):
            return DependencyManager.PIPENV

    # Fallback to pip
    return DependencyManager.PIP


def _extract_from_pyproject(
    project_path: Path, fs: FileSystem | None = None
) -> ProjectInfo | None:
    """Extract project info from pyproject.toml."""
    pyproject = project_path / "pyproject.toml"
    if not _fs_exists(pyproject, fs):
        return None

    data = _read_toml(pyproject, fs)
    if data is None:
        return None
    project = data.get("project", {})

    name = project.get("name")
    version = project.get("version")

    if not name:
        return None

    # Try dynamic version from tool sections
    if not version:
        version = "0.0.0"

    python_requires = project.get("requires-python")
    dependencies = project.get("dependencies", [])

    extras: dict[str, list[str]] = {}
    optional_deps = project.get("optional-dependencies", {})
    for extra_name, extra_deps in optional_deps.items():
        extras[extra_name] = list(extra_deps)

    return ProjectInfo(
        path=project_path,
        name=name,
        version=version,
        python_requires=python_requires,
        dependencies=dependencies,
        extras=extras,
    )


def _extract_from_setup_cfg(
    project_path: Path, fs: FileSystem | None = None
) -> ProjectInfo | None:
    """Extract project info from setup.cfg."""
    setup_cfg = project_path / "setup.cfg"
    if not _fs_exists(setup_cfg, fs):
        return None

    config = configparser.ConfigParser()
    with (fs or _DEFAULT_FS).open(str(setup_cfg), "r") as f:
        config.read_file(f)

    if not config.has_section("metadata"):
        return None

    name = config.get("metadata", "name", fallback=None)
    version = config.get("metadata", "version", fallback="0.0.0")

    if not name:
        return None

    python_requires = config.get("options", "python_requires", fallback=None)

    dependencies: list[str] = []
    install_requires = config.get("options", "install_requires", fallback="")
    if install_requires:
        dependencies = [
            dep.strip() for dep in install_requires.strip().splitlines() if dep.strip()
        ]

    extras: dict[str, list[str]] = {}
    if config.has_section("options.extras_require"):
        for extra_name in config.options("options.extras_require"):
            extra_deps = config.get("options.extras_require", extra_name)
            extras[extra_name] = [
                dep.strip() for dep in extra_deps.strip().splitlines() if dep.strip()
            ]

    return ProjectInfo(
        path=project_path,
        name=name,
        version=version,
        python_requires=python_requires,
        dependencies=dependencies,
        extras=extras,
    )


def _extract_from_requirements_txt(
    project_path: Path, fs: FileSystem | None = None
) -> ProjectInfo | None:
    """Extract dependencies from requirements.txt (limited info)."""
    req_file = project_path / "requirements.txt"
    if not _fs_exists(req_file, fs):
        return None

    content = _fs_read_text(req_file, fs)
    dependencies: list[str] = []
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("-") or line.startswith("--"):
            continue
        # Skip inline comments
        line = line.split("#")[0].strip()
        if line:
            dependencies.append(line)

    name = project_path.name
    return ProjectInfo(
        path=project_path,
        name=name,
        version="0.0.0",
        dependencies=dependencies,
    )


def _extract_from_pipfile_lock(
    project_path: Path, fs: FileSystem | None = None
) -> ProjectInfo | None:
    """Extract dependencies from Pipfile.lock."""
    lockfile = project_path / "Pipfile.lock"
    if not _fs_exists(lockfile, fs):
        return None

    content = _fs_read_text(lockfile, fs)
    data = json.loads(content)
    dependencies: list[str] = []

    for pkg_name, pkg_info in data.get("default", {}).items():
        version = pkg_info.get("version", "")
        if version:
            dependencies.append(f"{pkg_name}{version}")
        else:
            dependencies.append(pkg_name)

    name = project_path.name
    return ProjectInfo(
        path=project_path,
        name=name,
        version="0.0.0",
        dependencies=dependencies,
    )


def detect_project(
    project_path: Path, filesystem: FileSystem | None = None
) -> ProjectInfo:
    """Detect the project type and extract project information.

    Args:
        project_path: Path to the project root.
        filesystem: Optional filesystem for reading project files.
                    Accepts any fsspec-compatible filesystem.

    Returns:
        ProjectInfo with detected manager set.

    Raises:
        FileNotFoundError: If project_path does not exist.
        ValueError: If no project configuration can be found.
    """
    project_path = project_path.resolve()

    if not _fs_exists(project_path, filesystem):
        raise FileNotFoundError(f"Project path does not exist: {project_path}")

    if filesystem is None and not project_path.is_dir():
        raise ValueError(f"Project path is not a directory: {project_path}")

    manager = _detect_manager(project_path, filesystem)

    # Try extraction in order of preference
    info = (
        _extract_from_pyproject(project_path, filesystem)
        or _extract_from_setup_cfg(project_path, filesystem)
        or _extract_from_pipfile_lock(project_path, filesystem)
        or _extract_from_requirements_txt(project_path, filesystem)
    )

    if info is None:
        raise ValueError(
            f"Could not detect project configuration in: {project_path}. "
            "Expected one of: pyproject.toml, setup.cfg, Pipfile.lock, requirements.txt"
        )

    info.manager = manager
    return info
