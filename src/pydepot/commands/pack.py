"""Pack subcommand implementation."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from pydepot.models import PackOptions
from pydepot.packer import PackBuilder

logger = logging.getLogger(__name__)


def run_pack(args: argparse.Namespace) -> int:
    """Execute the pack subcommand."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    options = PackOptions(
        project_path=Path(args.project_path),
        output_dir=Path(args.output),
        platforms=args.platforms or [],
        python_version=args.python_version,
        exclude=args.exclude,
        include_extras=args.include_extras,
    )

    try:
        builder = PackBuilder(options)
        tarball_path = builder.build()
        print(f"Bundle created: {tarball_path}")
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
