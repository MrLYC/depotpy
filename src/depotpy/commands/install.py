"""Install subcommand implementation."""

from __future__ import annotations

import argparse
from pathlib import Path

from depotpy.installer import BundleInstaller
from depotpy.models import ConflictPolicy
from depotpy.output import error_json, print_error, print_json, print_text, setup_logging


def _get_verbosity(args: argparse.Namespace) -> int:
    """Extract verbosity level from parsed args."""
    if getattr(args, "verbose", False):
        return 1
    if getattr(args, "quiet", False):
        return -1
    return 0


def run_install(args: argparse.Namespace) -> int:
    """Execute the install subcommand."""
    setup_logging(_get_verbosity(args))
    json_output = getattr(args, "json_output", False)

    bundle_path_str = args.bundle_path
    target = getattr(args, "target", None)
    on_conflict = ConflictPolicy(getattr(args, "on_conflict", "keep"))

    # Detect remote filesystem from bundle URL
    fs = None
    if "://" in bundle_path_str:
        from depotpy.fs import filesystem_from_url
        fs, bundle_path_str = filesystem_from_url(bundle_path_str)

    bundle_path = Path(bundle_path_str)

    try:
        installer = BundleInstaller(bundle_path, filesystem=fs)
        installer.install(target=target, on_conflict=on_conflict)
        if json_output:
            print_json({
                "success": True,
                "bundle_path": str(bundle_path),
                "on_conflict": on_conflict.value,
            })
        else:
            print_text(f"Successfully installed packages from: {bundle_path}")
        return 0
    except (FileNotFoundError, ValueError, RuntimeError) as e:
        if json_output:
            error_json(str(e))
        else:
            print_error(str(e))
        return 1
