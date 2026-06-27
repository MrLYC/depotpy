"""CLI entry point for DepotPy."""

import argparse
import sys

from depotpy import __version__


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="depotpy",
        description="Build cross-platform offline installation packages for Python projects.",
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose (debug) output",
    )
    parser.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="Suppress informational output (warnings and errors only)",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # pack subcommand
    pack_parser = subparsers.add_parser(
        "pack", help="Build an offline installation package"
    )
    pack_parser.add_argument(
        "project_path",
        help="Path to the Python project to pack",
    )
    pack_parser.add_argument(
        "-o", "--output",
        default=".",
        help="Output directory for the bundle (default: current directory)",
    )
    pack_parser.add_argument(
        "--platform",
        action="append",
        dest="platforms",
        help="Target platform (can be specified multiple times, or 'all' for all common platforms)",
    )
    pack_parser.add_argument(
        "--python-version",
        help="Override Python version (e.g. '3.11')",
    )
    pack_parser.add_argument(
        "--exclude",
        action="append",
        default=[],
        help="Exclude a dependency (can be specified multiple times)",
    )
    pack_parser.add_argument(
        "--include-extras",
        action="append",
        default=[],
        help="Include extras dependencies (can be specified multiple times)",
    )
    pack_parser.add_argument(
        "--prefer",
        choices=["wheel", "source"],
        default="wheel",
        help="Prefer wheel or source packages (default: wheel)",
    )
    pack_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be downloaded without actually downloading",
    )
    pack_parser.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="Output result as JSON to stdout",
    )

    # inspect subcommand
    inspect_parser = subparsers.add_parser(
        "inspect", help="Inspect an offline installation bundle"
    )
    inspect_parser.add_argument(
        "bundle_path",
        help="Path to the offline bundle (.tar.gz)",
    )
    inspect_parser.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="Output result as JSON to stdout",
    )

    # install subcommand
    install_parser = subparsers.add_parser(
        "install", help="Install from an offline bundle"
    )
    install_parser.add_argument(
        "bundle_path",
        help="Path to the offline bundle (.tar.gz)",
    )
    install_parser.add_argument(
        "--target",
        help="Install packages into the specified directory",
    )
    install_parser.add_argument(
        "--on-conflict",
        choices=["keep", "overwrite", "error"],
        default="keep",
        help="How to handle conflicts with installed packages (default: keep)",
    )
    install_parser.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="Output result as JSON to stdout",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = create_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 0

    if args.command == "pack":
        from depotpy.commands.pack import run_pack
        return run_pack(args)
    elif args.command == "inspect":
        from depotpy.commands.inspect import run_inspect
        return run_inspect(args)
    elif args.command == "install":
        from depotpy.commands.install import run_install
        return run_install(args)

    return 0


if __name__ == "__main__":
    sys.exit(main())
