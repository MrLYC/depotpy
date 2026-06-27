"""Inspect subcommand implementation."""

from __future__ import annotations

import argparse
import json
import tarfile
from pathlib import Path

from depotpy.manifest import manifest_from_dict
from depotpy.output import error_json, print_error, print_json, print_text, setup_logging


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
        """Print a human-readable summary to stderr."""
        data = self.get_manifest()
        manifest = manifest_from_dict(data)

        print_text(f"Bundle: {self.bundle_path.name}")
        print_text(f"Project: {manifest.project_name} {manifest.project_version}")
        print_text(f"Python: {manifest.python_version}")
        print_text(f"Platforms: {', '.join(manifest.platforms)}")
        print_text(f"Packages: {manifest.package_count}")
        print_text(f"Total size: {manifest.total_size / 1024 / 1024:.1f} MB")
        print_text("")
        print_text("Package list:")
        for pkg in sorted(manifest.packages, key=lambda p: p.name):
            kind = "wheel" if pkg.is_wheel else "sdist"
            platforms = ", ".join(pkg.platform_tags) if pkg.platform_tags else "any"
            print_text(f"  {pkg.name} {pkg.version} ({kind}, {platforms}, {pkg.size / 1024:.0f} KB)")


def _get_verbosity(args: argparse.Namespace) -> int:
    """Extract verbosity level from parsed args."""
    if getattr(args, "verbose", False):
        return 1
    if getattr(args, "quiet", False):
        return -1
    return 0


def run_inspect(args: argparse.Namespace) -> int:
    """Execute the inspect subcommand."""
    setup_logging(_get_verbosity(args))
    json_output = getattr(args, "json_output", False)
    bundle_path = Path(args.bundle_path)

    try:
        inspector = BundleInspector(bundle_path)
        if json_output:
            data = inspector.get_manifest()
            data["success"] = True
            print_json(data)
        else:
            inspector.print_summary()
        return 0
    except (FileNotFoundError, ValueError) as e:
        if json_output:
            error_json(str(e))
        else:
            print_error(str(e))
        return 1
