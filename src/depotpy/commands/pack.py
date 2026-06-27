"""Pack subcommand implementation."""

from __future__ import annotations

import argparse
from pathlib import Path

from depotpy.detector import detect_project
from depotpy.manifest import manifest_to_dict
from depotpy.models import PackagePreference, PackOptions
from depotpy.output import error_json, print_error, print_json, print_text, setup_logging
from depotpy.packer import PackBuilder
from depotpy.platforms import get_python_version, resolve_platforms


def _run_dry_run(args: argparse.Namespace) -> int:
    """Show what would be packed without actually downloading."""
    json_output = getattr(args, "json_output", False)
    project_path = Path(args.project_path)

    try:
        project_info = detect_project(project_path)
        platforms = resolve_platforms(args.platforms or None)
        python_version = args.python_version or get_python_version()

        dependencies = list(project_info.dependencies)
        include_extras = args.include_extras or []
        for extra in include_extras:
            if extra in project_info.extras:
                dependencies.extend(project_info.extras[extra])

        excluded = {e.lower() for e in (args.exclude or [])}
        filtered_deps = [
            dep for dep in dependencies
            if dep.split(">=")[0].split("==")[0].split("[")[0].strip().lower() not in excluded
        ]

        if json_output:
            print_json({
                "success": True,
                "dry_run": True,
                "project_name": project_info.name,
                "project_version": project_info.version,
                "manager": project_info.manager.value if project_info.manager else "unknown",
                "python_version": python_version,
                "platforms": [str(p) for p in platforms],
                "dependencies": filtered_deps,
            })
        else:
            print_text(f"Project: {project_info.name} {project_info.version}")
            print_text(f"Manager: {project_info.manager.value if project_info.manager else 'unknown'}")
            print_text(f"Python: {python_version}")
            print_text(f"Platforms: {', '.join(str(p) for p in platforms)}")
            print_text(f"Dependencies ({len(filtered_deps)}):")
            for dep in sorted(filtered_deps):
                print_text(f"  - {dep}")
        return 0
    except (FileNotFoundError, ValueError) as e:
        if json_output:
            error_json(str(e))
        else:
            print_error(str(e))
        return 1


def _get_verbosity(args: argparse.Namespace) -> int:
    """Extract verbosity level from parsed args."""
    if getattr(args, "verbose", False):
        return 1
    if getattr(args, "quiet", False):
        return -1
    return 0


def run_pack(args: argparse.Namespace) -> int:
    """Execute the pack subcommand."""
    setup_logging(_get_verbosity(args))
    json_output = getattr(args, "json_output", False)

    if getattr(args, "dry_run", False):
        return _run_dry_run(args)

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
