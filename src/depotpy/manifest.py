"""Manifest generation and reading."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from depotpy.models import Manifest, PackageFile


def manifest_to_dict(manifest: Manifest) -> dict:
    """Convert a Manifest to a JSON-serializable dict."""
    return {
        "project_name": manifest.project_name,
        "project_version": manifest.project_version,
        "python_version": manifest.python_version,
        "platforms": manifest.platforms,
        "created_by": manifest.created_by,
        "package_count": manifest.package_count,
        "total_size": manifest.total_size,
        "packages": [
            {
                "filename": p.filename,
                "name": p.name,
                "version": p.version,
                "sha256": p.sha256,
                "size": p.size,
                "platform_tags": list(p.platform_tags),
            }
            for p in manifest.packages
        ],
    }


def manifest_from_dict(data: dict) -> Manifest:
    """Reconstruct a Manifest from a dict (e.g. loaded from JSON)."""
    packages = [
        PackageFile(
            filename=p["filename"],
            name=p["name"],
            version=p["version"],
            sha256=p["sha256"],
            size=p["size"],
            platform_tags=p.get("platform_tags", []),
        )
        for p in data.get("packages", [])
    ]

    return Manifest(
        project_name=data["project_name"],
        project_version=data["project_version"],
        python_version=data["python_version"],
        platforms=data.get("platforms", []),
        packages=packages,
        created_by=data.get("created_by", "depotpy"),
    )


def write_manifest(manifest: Manifest, path: Path) -> None:
    """Write a manifest to a JSON file."""
    data = manifest_to_dict(manifest)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")


def read_manifest(path: Path) -> Manifest:
    """Read a manifest from a JSON file.

    Raises:
        FileNotFoundError: If the manifest file does not exist.
        json.JSONDecodeError: If the file is not valid JSON.
        KeyError: If required fields are missing.
    """
    with open(path) as f:
        data = json.load(f)
    return manifest_from_dict(data)
