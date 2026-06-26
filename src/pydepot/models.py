"""Data models for PyDepot."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class DependencyManager(Enum):
    """Supported dependency managers."""

    UV = "uv"
    POETRY = "poetry"
    PDM = "pdm"
    PIPENV = "pipenv"
    PIP = "pip"


@dataclass
class ProjectInfo:
    """Information about the Python project to pack."""

    path: Path
    name: str
    version: str
    python_requires: str | None = None
    dependencies: list[str] = field(default_factory=list)
    extras: dict[str, list[str]] = field(default_factory=dict)
    manager: DependencyManager | None = None


@dataclass(frozen=True)
class PackageFile:
    """Represents a downloaded package file (wheel or sdist)."""

    filename: str
    name: str
    version: str
    sha256: str
    size: int
    platform_tags: list[str] = field(default_factory=list)

    @property
    def is_wheel(self) -> bool:
        return self.filename.endswith(".whl")

    @property
    def is_sdist(self) -> bool:
        return self.filename.endswith((".tar.gz", ".zip"))


@dataclass
class Manifest:
    """The manifest.json content for an offline bundle."""

    project_name: str
    project_version: str
    python_version: str
    platforms: list[str]
    packages: list[PackageFile] = field(default_factory=list)
    created_by: str = "pydepot"

    @property
    def total_size(self) -> int:
        return sum(p.size for p in self.packages)

    @property
    def package_count(self) -> int:
        return len(self.packages)


@dataclass
class PackOptions:
    """Options for the pack command."""

    project_path: Path
    output_dir: Path
    platforms: list[str] = field(default_factory=list)
    python_version: str | None = None
    exclude: list[str] = field(default_factory=list)
    include_extras: list[str] = field(default_factory=list)
