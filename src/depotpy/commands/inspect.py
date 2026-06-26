"""Inspect subcommand implementation."""

from __future__ import annotations

import argparse
import json
import sys
import tarfile
from pathlib import Path

from depotpy.manifest import manifest_from_dict


class BundleInspector:
    """Inspect an offline installation bundle."""

    def __init__(self, bundle_path: Path) -> None:
        self.bundle_path = bundle_path

    def get_manifest(self) -> dict:
        """Extract and return the manifest data from the bundle.

        Raises:
            FileNotFoundError: If bundle doesn't exist.
            ValueError: If bundle doesn't contain a manifest.
        """
        if not self.bundle_path.exists():
            raise FileNotFoundError(f"Bundle not found: {self.bundle_path}")

        with tarfile.open(self.bundle_path, "r:gz") as tar:
            for member in tar.getmembers():
                if member.name.endswith("/manifest.json"):
                    f = tar.extractfile(member)
                    if f is not None:
                        return json.load(f)

        raise ValueError(f"No manifest.json found in bundle: {self.bundle_path}")

    def print_summary(self) -> None:
        """Print a human-readable summary of the bundle."""
        data = self.get_manifest()
        manifest = manifest_from_dict(data)

        print(f"Bundle: {self.bundle_path.name}")
        print(f"Project: {manifest.project_name} {manifest.project_version}")
        print(f"Python: {manifest.python_version}")
        print(f"Platforms: {', '.join(manifest.platforms)}")
        print(f"Packages: {manifest.package_count}")
        print(f"Total size: {manifest.total_size / 1024 / 1024:.1f} MB")
        print()
        print("Package list:")
        for pkg in sorted(manifest.packages, key=lambda p: p.name):
            kind = "wheel" if pkg.is_wheel else "sdist"
            platforms = ", ".join(pkg.platform_tags) if pkg.platform_tags else "any"
            print(f"  {pkg.name} {pkg.version} ({kind}, {platforms}, {pkg.size / 1024:.0f} KB)")


def run_inspect(args: argparse.Namespace) -> int:
    """Execute the inspect subcommand."""
    bundle_path = Path(args.bundle_path)

    try:
        inspector = BundleInspector(bundle_path)
        inspector.print_summary()
        return 0
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
