"""Dependency resolution and wheel download using external tools."""

from __future__ import annotations

import hashlib
import logging
import os
import subprocess
from pathlib import Path

from depotpy.models import DependencyManager, PackageFile, ProjectInfo
from depotpy.platforms import PlatformTag

logger = logging.getLogger(__name__)


def _compute_sha256(filepath: Path) -> str:
    """Compute SHA-256 hash of a file."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _scan_downloaded_files(download_dir: Path) -> list[PackageFile]:
    """Scan a directory for downloaded package files and build PackageFile objects."""
    packages: list[PackageFile] = []

    for filepath in sorted(download_dir.iterdir()):
        if not filepath.is_file():
            continue
        filename = filepath.name

        if filename.endswith(".whl"):
            # Wheel filename format: {name}-{ver}(-{build})-{python}-{abi}-{platform}.whl
            parts = filename[:-4].split("-")
            name = parts[0]
            version = parts[1]
            # Platform tag is the last part
            platform_tag = parts[-1]
            platform_tags = [] if platform_tag == "any" else [platform_tag]
        elif filename.endswith(".tar.gz"):
            # sdist: {name}-{ver}.tar.gz
            base = filename[:-7]
            parts = base.rsplit("-", 1)
            name = parts[0] if len(parts) == 2 else base
            version = parts[1] if len(parts) == 2 else "0.0.0"
            platform_tags = []
        elif filename.endswith(".zip"):
            base = filename[:-4]
            parts = base.rsplit("-", 1)
            name = parts[0] if len(parts) == 2 else base
            version = parts[1] if len(parts) == 2 else "0.0.0"
            platform_tags = []
        else:
            continue

        sha256 = _compute_sha256(filepath)
        size = filepath.stat().st_size

        packages.append(
            PackageFile(
                filename=filename,
                name=name,
                version=version,
                sha256=sha256,
                size=size,
                platform_tags=platform_tags,
            )
        )

    return packages


def _build_pip_download_cmd(
    dependencies: list[str],
    download_dir: Path,
    platform: PlatformTag,
    python_version: str | None = None,
    exclude: list[str] | None = None,
) -> list[str]:
    """Build a pip download command."""
    cmd = [
        "pip", "download",
        "--dest", str(download_dir),
        "--platform", platform.tag,
        "--only-binary=:all:",
    ]

    if python_version:
        # Convert "3.11" to "311" for pip
        py_ver = python_version.replace(".", "")
        cmd.extend(["--python-version", py_ver])

    excluded = set(exclude or [])
    for dep in dependencies:
        dep_name = dep.split(">=")[0].split("==")[0].split("<=")[0].split("!=")[0].split("<")[0].split(">")[0].split("[")[0].strip()
        if dep_name.lower() not in {e.lower() for e in excluded}:
            cmd.append(dep)

    return cmd


def _build_uv_download_cmd(
    dependencies: list[str],
    download_dir: Path,
    platform: PlatformTag,
    python_version: str | None = None,
    exclude: list[str] | None = None,
) -> list[str]:
    """Build a uv pip download command."""
    cmd = [
        "uv", "pip", "download",
        "--dest", str(download_dir),
        "--platform", platform.tag,
        "--only-binary=:all:",
    ]

    if python_version:
        cmd.extend(["--python-version", python_version])

    excluded = set(exclude or [])
    for dep in dependencies:
        dep_name = dep.split(">=")[0].split("==")[0].split("<=")[0].split("!=")[0].split("<")[0].split(">")[0].split("[")[0].strip()
        if dep_name.lower() not in {e.lower() for e in excluded}:
            cmd.append(dep)

    return cmd


def _run_download_cmd(cmd: list[str], download_dir: Path) -> None:
    """Run a download command and raise on failure."""
    logger.info("Running: %s", " ".join(cmd))

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=str(download_dir.parent),
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"Download command failed (exit code {result.returncode}):\n"
            f"Command: {' '.join(cmd)}\n"
            f"stderr: {result.stderr}"
        )

    if result.stdout:
        logger.debug("stdout: %s", result.stdout)


def _download_for_platform_pip(
    dependencies: list[str],
    download_dir: Path,
    platform: PlatformTag,
    python_version: str | None = None,
    exclude: list[str] | None = None,
) -> None:
    """Download packages for a specific platform using pip."""
    if not dependencies:
        return

    cmd = _build_pip_download_cmd(
        dependencies, download_dir, platform, python_version, exclude
    )
    _run_download_cmd(cmd, download_dir)


def _download_for_platform_uv(
    dependencies: list[str],
    download_dir: Path,
    platform: PlatformTag,
    python_version: str | None = None,
    exclude: list[str] | None = None,
) -> None:
    """Download packages for a specific platform using uv."""
    if not dependencies:
        return

    cmd = _build_uv_download_cmd(
        dependencies, download_dir, platform, python_version, exclude
    )
    _run_download_cmd(cmd, download_dir)


def download_packages(
    project_info: ProjectInfo,
    download_dir: Path,
    platforms: list[PlatformTag],
    python_version: str | None = None,
    exclude: list[str] | None = None,
    include_extras: list[str] | None = None,
) -> list[PackageFile]:
    """Download all dependency packages for the given platforms.

    Args:
        project_info: Detected project information.
        download_dir: Directory to download packages into.
        platforms: List of target platforms.
        python_version: Override Python version.
        exclude: Dependencies to exclude.
        include_extras: Extras to include.

    Returns:
        List of PackageFile objects for all downloaded files.

    Raises:
        RuntimeError: If download fails.
    """
    download_dir.mkdir(parents=True, exist_ok=True)

    # Collect all dependencies
    dependencies = list(project_info.dependencies)
    if include_extras:
        for extra in include_extras:
            if extra in project_info.extras:
                dependencies.extend(project_info.extras[extra])

    if not dependencies:
        logger.warning("No dependencies found to download.")
        return []

    # Choose download function based on manager
    if project_info.manager == DependencyManager.UV:
        download_fn = _download_for_platform_uv
    else:
        download_fn = _download_for_platform_pip

    # Download for each platform
    for platform in platforms:
        logger.info("Downloading packages for platform: %s", platform.tag)
        try:
            download_fn(
                dependencies=dependencies,
                download_dir=download_dir,
                platform=platform,
                python_version=python_version,
                exclude=exclude,
            )
        except RuntimeError:
            # If the preferred tool fails and it's not pip, retry with pip
            if project_info.manager != DependencyManager.PIP:
                logger.warning(
                    "Download with %s failed for %s, falling back to pip",
                    project_info.manager.value,
                    platform.tag,
                )
                _download_for_platform_pip(
                    dependencies=dependencies,
                    download_dir=download_dir,
                    platform=platform,
                    python_version=python_version,
                    exclude=exclude,
                )
            else:
                raise

    return _scan_downloaded_files(download_dir)
