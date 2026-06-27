"""Shared output and logging utilities."""

from __future__ import annotations

import json
import logging
import sys


def setup_logging(verbosity: int = 0) -> None:
    """Configure logging to output to stderr.

    Args:
        verbosity: -1 for quiet (WARNING+), 0 for normal (INFO), 1 for verbose (DEBUG).
    """
    if verbosity >= 1:
        level = logging.DEBUG
    elif verbosity <= -1:
        level = logging.WARNING
    else:
        level = logging.INFO

    logging.basicConfig(
        level=level,
        format="%(levelname)s: %(message)s",
        stream=sys.stderr,
        force=True,
    )


def print_json(data: dict) -> None:
    """Print a JSON object to stdout."""
    json.dump(data, sys.stdout, indent=2)
    sys.stdout.write("\n")


def print_text(message: str) -> None:
    """Print a human-readable message to stderr."""
    print(message, file=sys.stderr)


def print_error(message: str) -> None:
    """Print an error message to stderr."""
    print(f"Error: {message}", file=sys.stderr)


def error_json(message: str) -> None:
    """Print an error as JSON to stdout."""
    print_json({"success": False, "error": str(message)})
