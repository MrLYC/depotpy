"""Pack subcommand implementation."""

from __future__ import annotations

import argparse
from pathlib import Path

from depotpy.manifest import manifest_to_dict
from depotpy.models import PackagePreference, PackOptions
from depotpy.output import error_json, print_error, print_json, print_text, setup_logging
from depotpy.packer import PackBuilder


def run_pack(args: argparse.Namespace) -> int:
    """Execute the pack subcommand."""
    setup_logging()
    json_output = getattr(args, "json_output", False)

    options = PackOptions(
        project_path=Path(args.project_path),
        output_dir=Path(args.output),
        platforms=args.platforms or [],
        python_version=args.python_version,
        exclude=args.exclude,
        include_extras=args.include_extras,
        prefer=PackagePreference(args.prefer),
    )

    try:
        builder = PackBuilder(options)
        tarball_path, manifest = builder.build()
        if json_output:
            result = manifest_to_dict(manifest)
            result["bundle_path"] = str(tarball_path)
            result["success"] = True
            print_json(result)
        else:
            print_text(f"Bundle created: {tarball_path}")
        return 0
    except (FileNotFoundError, ValueError, RuntimeError) as e:
        if json_output:
            error_json(str(e))
        else:
            print_error(str(e))
        return 1
