"""Install subcommand implementation."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from depotpy.installer import BundleInstaller
from depotpy.models import ConflictPolicy

logger = logging.getLogger(__name__)


def run_install(args: argparse.Namespace) -> int:
    """Execute the install subcommand."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    bundle_path = Path(args.bundle_path)
    target = getattr(args, "target", None)
    on_conflict = ConflictPolicy(getattr(args, "on_conflict", "keep"))

    try:
        installer = BundleInstaller(bundle_path)
        installer.install(target=target, on_conflict=on_conflict)
        print(f"Successfully installed packages from: {bundle_path}")
        return 0
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
