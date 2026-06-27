"""Install from offline bundle."""

from __future__ import annotations

import json
import logging
import subprocess
import tarfile
import tempfile
from pathlib import Path

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
            ["pip", "list", "--format=json"],
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


class BundleInstaller:
    """Install packages from an offline bundle."""

    def __init__(self, bundle_path: Path) -> None:
        self.bundle_path = bundle_path

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
        if not self.bundle_path.exists():
            raise FileNotFoundError(f"Bundle not found: {self.bundle_path}")

        with tempfile.TemporaryDirectory() as tmp_dir:
            extract_dir = Path(tmp_dir)

            # Extract the bundle
            with tarfile.open(self.bundle_path, "r:gz") as tar:
                tar.extractall(path=extract_dir, filter="data")

            # Find the manifest
            manifest, packages_dir = self._find_manifest_and_packages(extract_dir)

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
        package_names = sorted({p.name for p in manifest.packages})

        cmd = [
            "pip", "install",
            "--no-index",
            "--find-links", str(packages_dir),
        ]

        if on_conflict == ConflictPolicy.OVERWRITE:
            cmd.append("--force-reinstall")

        if target:
            cmd.extend(["--target", target])

        cmd.extend(package_names)
        return cmd
