"""Install from offline bundle."""

from __future__ import annotations

import hashlib
import json
import logging
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path
from typing import Any

from depotpy.fs import FileSystem, is_local, local_copy
from depotpy.manifest import manifest_from_dict
from depotpy.models import ConflictPolicy, Manifest

logger = logging.getLogger(__name__)


def _get_installed_packages() -> dict[str, str]:
    """Get a mapping of installed package names (lowercase) to versions.

    Returns empty dict if pip is unavailable. Raises RuntimeError if pip
    succeeds but output cannot be parsed.
    """
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "list", "--format=json"],
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        logger.warning("pip not found; skipping installed package check")
        return {}

    if result.returncode != 0:
        logger.warning("pip list failed (exit %d); skipping installed package check", result.returncode)
        return {}

    try:
        installed: dict[str, str] = {}
        for pkg in json.loads(result.stdout):
            installed[pkg["name"].lower()] = pkg["version"]
        return installed
    except (json.JSONDecodeError, KeyError) as e:
        raise RuntimeError(f"Failed to parse pip list output: {e}") from e


def _check_conflicts(
    manifest: Manifest, installed: dict[str, str]
) -> list[str]:
    """Check for version conflicts between bundle packages and installed packages.

    Returns a list of conflict description strings (empty if no conflicts).
    """
    conflicts: list[str] = []
    for pkg in manifest.packages:
        pkg_name = pkg.name.lower().replace("-", "_").replace(".", "_")
        for inst_name, inst_version in installed.items():
            norm_inst = inst_name.lower().replace("-", "_").replace(".", "_")
            if pkg_name == norm_inst and inst_version != pkg.version:
                conflicts.append(
                    f"{pkg.name}: installed {inst_version}, bundle has {pkg.version}"
                )
                break
    return conflicts


def _compute_sha256(filepath: Path) -> str:
    """Compute SHA-256 hash of a file."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _validate_manifest_files(manifest: Manifest, packages_dir: Path) -> list[Path]:
    """Validate manifest package files and return exact install paths."""
    package_paths: list[Path] = []
    for pkg in manifest.packages:
        package_path = packages_dir / Path(pkg.filename).name
        if not package_path.exists():
            raise RuntimeError(f"Package file missing from bundle: {pkg.filename}")

        actual_size = package_path.stat().st_size
        if actual_size != pkg.size:
            raise RuntimeError(
                f"Package size mismatch for {pkg.filename}: "
                f"expected {pkg.size}, got {actual_size}"
            )

        actual_sha256 = _compute_sha256(package_path)
        if actual_sha256 != pkg.sha256:
            raise RuntimeError(
                f"Package SHA-256 mismatch for {pkg.filename}: "
                f"expected {pkg.sha256}, got {actual_sha256}"
            )

        package_paths.append(package_path)

    return package_paths


def _install_requirements(manifest: Manifest) -> list[str]:
    """Return pinned requirements for pip to resolve from verified local files."""
    return sorted({f"{pkg.name}=={pkg.version}" for pkg in manifest.packages})


class BundleInstaller:
    """Install packages from an offline bundle."""

    def __init__(
        self,
        bundle_path: Path | str,
        filesystem: FileSystem | None = None,
    ) -> None:
        """Initialize the installer.

        Args:
            bundle_path: Path to the bundle file.
            filesystem: Optional filesystem for reading remote bundles.
                        Accepts any fsspec-compatible filesystem.
        """
        self.bundle_path = Path(bundle_path) if isinstance(bundle_path, str) else bundle_path
        self._fs = filesystem

    def install(
        self,
        target: str | None = None,
        on_conflict: ConflictPolicy = ConflictPolicy.KEEP,
    ) -> None:
        """Extract the bundle and install packages using pip.

        Args:
            target: Optional target directory for pip install --target.
            on_conflict: How to handle conflicts with installed packages.

        Raises:
            FileNotFoundError: If bundle doesn't exist.
            ValueError: If bundle has no manifest.
            RuntimeError: If pip install fails or conflicts are found (with error policy).
        """
        if self._fs is not None and not is_local(self._fs):
            with local_copy(self._fs, str(self.bundle_path), suffix=".tar.gz") as local_bundle:
                self._do_install(local_bundle, target, on_conflict)
        else:
            if not self.bundle_path.exists():
                raise FileNotFoundError(f"Bundle not found: {self.bundle_path}")
            self._do_install(self.bundle_path, target, on_conflict)

    def _do_install(
        self,
        bundle_path: Path,
        target: str | None,
        on_conflict: ConflictPolicy,
    ) -> None:
        """Execute the installation from a local bundle path."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            extract_dir = Path(tmp_dir)

            # Extract the bundle
            with tarfile.open(bundle_path, "r:gz") as tar:
                tar.extractall(path=extract_dir, filter="data")

            # Find the manifest and validate package files before invoking pip
            manifest, packages_dir = self._find_manifest_and_packages(extract_dir)
            _validate_manifest_files(manifest, packages_dir)

            # Check conflicts if needed
            if on_conflict == ConflictPolicy.ERROR:
                installed = _get_installed_packages()
                conflicts = _check_conflicts(manifest, installed)
                if conflicts:
                    details = "\n".join(f"  - {c}" for c in conflicts)
                    raise RuntimeError(
                        f"Version conflicts detected:\n{details}\n"
                        "Use --on-conflict=keep to skip or "
                        "--on-conflict=overwrite to force reinstall."
                    )

            # Build pip install command
            cmd = self._build_install_cmd(manifest, packages_dir, target, on_conflict)

            logger.info("Running: %s", " ".join(cmd))
            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode != 0:
                raise RuntimeError(
                    f"pip install failed (exit code {result.returncode}):\n"
                    f"{result.stderr}"
                )

            if result.stdout:
                logger.info("%s", result.stdout)

    def _find_manifest_and_packages(
        self, extract_dir: Path
    ) -> tuple[Manifest, Path]:
        """Find the manifest.json and packages directory in the extracted bundle."""
        for manifest_path in extract_dir.rglob("manifest.json"):
            with open(manifest_path) as f:
                data = json.load(f)
            manifest = manifest_from_dict(data)
            packages_dir = manifest_path.parent / "packages"
            return manifest, packages_dir

        raise ValueError(f"No manifest.json found in bundle: {self.bundle_path}")

    def _build_install_cmd(
        self,
        manifest: Manifest,
        packages_dir: Path,
        target: str | None = None,
        on_conflict: ConflictPolicy = ConflictPolicy.KEEP,
    ) -> list[str]:
        """Build the pip install command."""
        cmd = [
            sys.executable, "-m", "pip", "install",
            "--no-index",
            "--find-links", str(packages_dir),
        ]

        if on_conflict == ConflictPolicy.OVERWRITE:
            cmd.append("--force-reinstall")

        if target:
            cmd.extend(["--target", target])

        cmd.extend(_install_requirements(manifest))
        return cmd
