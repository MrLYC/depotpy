# Getting Started

## Prerequisites

- Python 3.11 or later
- pip (bundled with Python)
- Optional: [uv](https://github.com/astral-sh/uv), [poetry](https://python-poetry.org/), [pdm](https://pdm-project.org/), or [pipenv](https://pipenv.pypa.io/) — DepotPy will use them if your project does

## Installation

```bash
pip install depotpy
```

Verify the installation:

```bash
depotpy --version
```

## Your First Offline Bundle

### 1. Pack

Navigate to any Python project that has a `pyproject.toml`, `setup.cfg`, or `requirements.txt`, then run:

```bash
depotpy pack .
```

This will:
1. Detect your dependency manager and project metadata
2. Download all dependency wheels for the current platform
3. Generate a `manifest.json` with versions and SHA-256 hashes
4. Create a `.tar.gz` bundle in the current directory

The output file is named `{project}-{version}-offline.tar.gz`.

### 2. Transfer

Copy the `.tar.gz` to the target machine via USB, SCP, or any other method:

```bash
scp myapp-1.0.0-offline.tar.gz user@target-host:/tmp/
```

### 3. Install

On the target machine (no internet required):

```bash
# Using DepotPy (if installed)
depotpy install myapp-1.0.0-offline.tar.gz

# Or manually
tar xzf myapp-1.0.0-offline.tar.gz
cd myapp-1.0.0-offline
pip install --no-index --find-links ./packages <package-names>
```

The exact `pip install` command is included in the bundle's `README.md`.

## Cross-Platform Bundles

To build a bundle that works on multiple platforms:

```bash
# Specify individual platforms
depotpy pack . --platform manylinux2014_x86_64 --platform macosx_11_0_arm64

# Use a preset
depotpy pack . --platform linux    # All Linux variants
depotpy pack . --platform macos    # macOS x86_64 + ARM
depotpy pack . --platform all      # All 8 platforms
```

Cross-platform bundles are larger because they include platform-specific wheels for each target. Pure-Python wheels (e.g. `requests`) are included only once.

## Inspecting Bundles

Before transferring, you can verify what's inside:

```bash
depotpy inspect myapp-1.0.0-offline.tar.gz
```

Output:
```
Bundle: myapp-1.0.0-offline.tar.gz
Project: myapp 1.0.0
Python: 3.11
Platforms: manylinux2014_x86_64
Packages: 5
Total size: 2.3 MB

Package list:
  certifi 2024.2.2 (wheel, any, 157 KB)
  charset-normalizer 3.3.2 (wheel, manylinux2014_x86_64, 140 KB)
  idna 3.6 (wheel, any, 62 KB)
  requests 2.31.0 (wheel, any, 62 KB)
  urllib3 2.2.1 (wheel, any, 218 KB)
```

## Common Options

```bash
# Override Python version
depotpy pack . --python-version 3.12

# Exclude specific dependencies
depotpy pack . --exclude pytest --exclude mypy

# Include optional extras
depotpy pack . --include-extras dev --include-extras docs

# Specify output directory
depotpy pack . -o /path/to/output/

# Prefer source distributions over wheels
depotpy pack . --prefer source

# Preview what will be downloaded without downloading (dry run)
depotpy pack . --platform all --dry-run

# Machine-readable JSON output (useful for scripting)
depotpy pack . --json
depotpy inspect myapp-1.0.0-offline.tar.gz --json

# Handle version conflicts during install
depotpy install bundle.tar.gz --on-conflict overwrite  # Force reinstall
depotpy install bundle.tar.gz --on-conflict error      # Fail on conflicts

# Verbose/quiet output
depotpy -v pack .    # Debug-level logging
depotpy -q pack .    # Warnings and errors only
```

## Next Steps

- [CLI Reference](cli-reference.md) — Full command-line documentation
- [Python API Reference](api-reference.md) — Use DepotPy as a library
- [Architecture](architecture.md) — How DepotPy works internally
