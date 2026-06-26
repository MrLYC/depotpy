"""Install from offline bundle."""

from __future__ import annotations

import json
import logging
import subprocess
import tarfile
import tempfile
from pathlib import Path

from pydepot.manifest import manifest_from_dict
from pydepot.models import Manifest

logger = logging.getLogger(__name__)


class BundleInstaller:
    """Install packages from an offline bundle."""

    def __init__(self, bundle_path: Path) -> None:
        self.bundle_path = bundle_path

    def install(self, target: str | None = None) -> None:
        """Extract the bundle and install packages using pip.

        Args:
            target: Optional target directory for pip install --target.

        Raises:
            FileNotFoundError: If bundle doesn't exist.
            ValueError: If bundle has no manifest.
            RuntimeError: If pip install fails.
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

            # Build pip install command
            cmd = self._build_install_cmd(manifest, packages_dir, target)

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
    ) -> list[str]:
        """Build the pip install command."""
        package_names = sorted({p.name for p in manifest.packages})

        cmd = [
            "pip", "install",
            "--no-index",
            "--find-links", str(packages_dir),
        ]

        if target:
            cmd.extend(["--target", target])

        cmd.extend(package_names)
        return cmd
