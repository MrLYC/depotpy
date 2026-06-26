"""Dependency manager detection and project info extraction."""

from __future__ import annotations

import configparser
import json
import shutil
from pathlib import Path

from depotpy.models import DependencyManager, ProjectInfo

try:
    import tomllib
except ImportError:
    import tomli as tomllib  # type: ignore[no-redef]


def _read_toml(path: Path) -> dict:
    """Read a TOML file and return its contents as a dict."""
    with open(path, "rb") as f:
        return tomllib.load(f)


def _detect_manager(project_path: Path) -> DependencyManager:
    """Detect the dependency manager used by the project.

    Priority: uv > poetry > pdm > pipenv > pip
    """
    pyproject = project_path / "pyproject.toml"

    if pyproject.exists():
        data = _read_toml(pyproject)
        tool = data.get("tool", {})

        # uv: check for uv.lock or [tool.uv]
        if (project_path / "uv.lock").exists() or "uv" in tool:
            if shutil.which("uv"):
                return DependencyManager.UV

        # poetry: check for poetry.lock or [tool.poetry]
        if (project_path / "poetry.lock").exists() or "poetry" in tool:
            if shutil.which("poetry"):
                return DependencyManager.POETRY

        # pdm: check for pdm.lock or [tool.pdm]
        if (project_path / "pdm.lock").exists() or "pdm" in tool:
            if shutil.which("pdm"):
                return DependencyManager.PDM

    # pipenv: check for Pipfile or Pipfile.lock
    if (project_path / "Pipfile").exists() or (project_path / "Pipfile.lock").exists():
        if shutil.which("pipenv"):
            return DependencyManager.PIPENV

    # Fallback to pip
    return DependencyManager.PIP


def _extract_from_pyproject(project_path: Path) -> ProjectInfo | None:
    """Extract project info from pyproject.toml."""
    pyproject = project_path / "pyproject.toml"
    if not pyproject.exists():
        return None

    data = _read_toml(pyproject)
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


def _extract_from_setup_cfg(project_path: Path) -> ProjectInfo | None:
    """Extract project info from setup.cfg."""
    setup_cfg = project_path / "setup.cfg"
    if not setup_cfg.exists():
        return None

    config = configparser.ConfigParser()
    config.read(setup_cfg)

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


def _extract_from_requirements_txt(project_path: Path) -> ProjectInfo | None:
    """Extract dependencies from requirements.txt (limited info)."""
    req_file = project_path / "requirements.txt"
    if not req_file.exists():
        return None

    dependencies: list[str] = []
    for line in req_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and not line.startswith("-"):
            dependencies.append(line)

    name = project_path.name
    return ProjectInfo(
        path=project_path,
        name=name,
        version="0.0.0",
        dependencies=dependencies,
    )


def _extract_from_pipfile_lock(project_path: Path) -> ProjectInfo | None:
    """Extract dependencies from Pipfile.lock."""
    lockfile = project_path / "Pipfile.lock"
    if not lockfile.exists():
        return None

    data = json.loads(lockfile.read_text())
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


def detect_project(project_path: Path) -> ProjectInfo:
    """Detect the project type and extract project information.

    Args:
        project_path: Path to the project root.

    Returns:
        ProjectInfo with detected manager set.

    Raises:
        FileNotFoundError: If project_path does not exist.
        ValueError: If no project configuration can be found.
    """
    project_path = project_path.resolve()

    if not project_path.exists():
        raise FileNotFoundError(f"Project path does not exist: {project_path}")

    if not project_path.is_dir():
        raise ValueError(f"Project path is not a directory: {project_path}")

    manager = _detect_manager(project_path)

    # Try extraction in order of preference
    info = (
        _extract_from_pyproject(project_path)
        or _extract_from_setup_cfg(project_path)
        or _extract_from_pipfile_lock(project_path)
        or _extract_from_requirements_txt(project_path)
    )

    if info is None:
        raise ValueError(
            f"Could not detect project configuration in: {project_path}. "
            "Expected one of: pyproject.toml, setup.cfg, Pipfile.lock, requirements.txt"
        )

    info.manager = manager
    return info
