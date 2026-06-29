"""Dependency resolution and wheel download using external tools."""

from __future__ import annotations

import hashlib
import logging
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from depotpy.models import DependencyManager, PackageFile, PackagePreference, ProjectInfo
from depotpy.platforms import PlatformTag

logger = logging.getLogger(__name__)


def _compute_sha256(filepath: Path) -> str:
    """Compute SHA-256 hash of a file."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _parse_wheel_filename(filename: str) -> tuple[str, str, list[str]]:
    """Parse a wheel filename into (name, version, platform_tags).

    Wheel format: {name}-{ver}(-{build})?-{python}-{abi}-{platform}.whl
    The last 3 fields (python, abi, platform) are always present.
    An optional build tag may appear between version and python tag.
    """
    stem = filename[:-4]  # strip .whl
    # Split from the right: platform, abi, python are the last 3 fields
    # There may be an optional build tag before them
    parts = stem.split("-")
    # At minimum: name, version, python, abi, platform = 5 parts
    # With build tag: name, version, build, python, abi, platform = 6+ parts
    # But name itself may contain hyphens (normalized to _ in wheels, but not always)
    platform_tag = parts[-1]
    # abi = parts[-2], python = parts[-3]
    # Check if there's a build tag: build tags are numeric
    if len(parts) >= 6 and parts[-4].isdigit():
        # Has build tag: name is everything before version (parts[-5])
        version = parts[-5]
        name = "-".join(parts[:-5])
    else:
        # No build tag: name is everything before version (parts[-4])
        version = parts[-4] if len(parts) >= 5 else parts[1] if len(parts) >= 2 else "0.0.0"
        name = "-".join(parts[:-4]) if len(parts) >= 5 else parts[0]

    platform_tags = [] if platform_tag == "any" else [platform_tag]
    return name, version, platform_tags


def _scan_downloaded_files(download_dir: Path) -> list[PackageFile]:
    """Scan a directory for downloaded package files and build PackageFile objects."""
    packages: list[PackageFile] = []

    for filepath in sorted(download_dir.iterdir()):
        if not filepath.is_file():
            continue
        filename = filepath.name

        if filename.endswith(".whl"):
            name, version, platform_tags = _parse_wheel_filename(filename)
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


def _binary_flag(prefer: PackagePreference) -> str:
    """Return the pip/uv binary preference flag."""
    if prefer == PackagePreference.SOURCE:
        return "--no-binary=:all:"
    return "--only-binary=:all:"


def _extract_dep_name(dep: str) -> str:
    """Extract the package name from a dependency specifier (PEP 508)."""
    match = re.match(r"([A-Za-z0-9]([A-Za-z0-9._-]*[A-Za-z0-9])?)", dep)
    return match.group(1) if match else dep.strip()


def _filter_dependencies(
    dependencies: list[str], exclude: list[str] | None = None
) -> list[str]:
    """Filter dependencies, removing excluded packages (case-insensitive)."""
    excluded = {e.lower() for e in (exclude or [])}
    return [
        dep for dep in dependencies
        if _extract_dep_name(dep).lower() not in excluded
    ]


def _build_download_cmd(
    base_cmd: list[str],
    dependencies: list[str],
    download_dir: Path,
    platform: PlatformTag,
    python_version: str | None = None,
    python_version_transform: str = "raw",
    exclude: list[str] | None = None,
    prefer: PackagePreference = PackagePreference.WHEEL,
) -> list[str]:
    """Build a download command for pip or uv.

    Args:
        base_cmd: Base command prefix (e.g. ["pip", "download"] or ["uv", "pip", "download"]).
        python_version_transform: "dotless" to convert "3.11" to "311" (pip), "raw" to keep as-is (uv).
    """
    cmd = [
        *base_cmd,
        "--dest", str(download_dir),
        "--platform", platform.tag,
        _binary_flag(prefer),
    ]

    if python_version:
        if python_version_transform == "dotless":
            py_ver = python_version.replace(".", "")
        else:
            py_ver = python_version
        cmd.extend(["--python-version", py_ver])

    cmd.extend(_filter_dependencies(dependencies, exclude))
    return cmd


def _build_pip_download_cmd(
    dependencies: list[str],
    download_dir: Path,
    platform: PlatformTag,
    python_version: str | None = None,
    exclude: list[str] | None = None,
    prefer: PackagePreference = PackagePreference.WHEEL,
) -> list[str]:
    """Build a pip download command."""
    return _build_download_cmd(
        [sys.executable, "-m", "pip", "download"], dependencies, download_dir, platform,
        python_version, "dotless", exclude, prefer,
    )


def _build_uv_download_cmd(
    dependencies: list[str],
    download_dir: Path,
    platform: PlatformTag,
    python_version: str | None = None,
    exclude: list[str] | None = None,
    prefer: PackagePreference = PackagePreference.WHEEL,
) -> list[str]:
    """Build a uv pip download command."""
    return _build_download_cmd(
        ["uv", "pip", "download"], dependencies, download_dir, platform,
        python_version, "raw", exclude, prefer,
    )


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
    prefer: PackagePreference = PackagePreference.WHEEL,
) -> None:
    """Download packages for a specific platform using pip."""
    if not dependencies:
        return

    cmd = _build_pip_download_cmd(
        dependencies, download_dir, platform, python_version, exclude, prefer
    )
    _run_download_cmd(cmd, download_dir)


def _download_for_platform_uv(
    dependencies: list[str],
    download_dir: Path,
    platform: PlatformTag,
    python_version: str | None = None,
    exclude: list[str] | None = None,
    prefer: PackagePreference = PackagePreference.WHEEL,
) -> None:
    """Download packages for a specific platform using uv."""
    if not dependencies:
        return

    cmd = _build_uv_download_cmd(
        dependencies, download_dir, platform, python_version, exclude, prefer
    )
    _run_download_cmd(cmd, download_dir)


def download_packages(
    project_info: ProjectInfo,
    download_dir: Path,
    platforms: list[PlatformTag],
    python_version: str | None = None,
    exclude: list[str] | None = None,
    include_extras: list[str] | None = None,
    prefer: PackagePreference = PackagePreference.WHEEL,
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

    def _download_one_platform(platform: PlatformTag) -> None:
        """Download packages for a single platform with fallback."""
        logger.info("Downloading packages for platform: %s", platform.tag)
        try:
            download_fn(
                dependencies=dependencies,
                download_dir=download_dir,
                platform=platform,
                python_version=python_version,
                exclude=exclude,
                prefer=prefer,
            )
        except RuntimeError:
            if project_info.manager != DependencyManager.PIP:
                logger.warning(
                    "Download with %s failed for %s, falling back to pip",
                    project_info.manager.value if project_info.manager else "unknown",
                    platform.tag,
                )
                _download_for_platform_pip(
                    dependencies=dependencies,
                    download_dir=download_dir,
                    platform=platform,
                    python_version=python_version,
                    exclude=exclude,
                    prefer=prefer,
                )
            else:
                raise

    # Download for each platform (parallel when multiple)
    total = len(platforms)
    if total <= 1:
        for i, platform in enumerate(platforms, 1):
            logger.info("[%d/%d] Starting download for %s", i, total, platform.tag)
            _download_one_platform(platform)
            logger.info("[%d/%d] Completed download for %s", i, total, platform.tag)
    else:
        completed = 0
        errors: list[Exception] = []
        with ThreadPoolExecutor(max_workers=min(total, 4)) as executor:
            futures = {
                executor.submit(_download_one_platform, p): p for p in platforms
            }
            for future in as_completed(futures):
                platform = futures[future]
                try:
                    future.result()
                    completed += 1
                    logger.info("[%d/%d] Completed download for %s", completed, total, platform.tag)
                except Exception as exc:
                    completed += 1
                    logger.error("[%d/%d] Download failed for %s: %s", completed, total, platform.tag, exc)
                    errors.append(exc)
        if errors:
            raise RuntimeError(
                f"Download failed for {len(errors)} platform(s): "
                + "; ".join(str(e) for e in errors)
            )

    return _scan_downloaded_files(download_dir)
