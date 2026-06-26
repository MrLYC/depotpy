# Getting Started

## Prerequisites

- Python 3.11 or later
- pip (bundled with Python)
- Optional: [uv](https://github.com/astral-sh/uv), [poetry](https://python-poetry.org/), [pdm](https://pdm-project.org/), or [pipenv](https://pipenv.pypa.io/) — PyDepot will use them if your project does

## Installation

```bash
pip install pydepot
```

Verify the installation:

```bash
pydepot --version
```

## Your First Offline Bundle

### 1. Pack

Navigate to any Python project that has a `pyproject.toml`, `setup.cfg`, or `requirements.txt`, then run:

```bash
pydepot pack .
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
# Using PyDepot (if installed)
pydepot install myapp-1.0.0-offline.tar.gz

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
pydepot pack . --platform manylinux2014_x86_64 --platform macosx_11_0_arm64

# Use a preset
pydepot pack . --platform linux    # All Linux variants
pydepot pack . --platform macos    # macOS x86_64 + ARM
pydepot pack . --platform all      # All 8 platforms
```

Cross-platform bundles are larger because they include platform-specific wheels for each target. Pure-Python wheels (e.g. `requests`) are included only once.

## Inspecting Bundles

Before transferring, you can verify what's inside:

```bash
pydepot inspect myapp-1.0.0-offline.tar.gz
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
pydepot pack . --python-version 3.12

# Exclude specific dependencies
pydepot pack . --exclude pytest --exclude mypy

# Include optional extras
pydepot pack . --include-extras dev --include-extras docs

# Specify output directory
pydepot pack . -o /path/to/output/
```

## Next Steps

- [CLI Reference](cli-reference.md) — Full command-line documentation
- [Python API Reference](api-reference.md) — Use PyDepot as a library
- [Architecture](architecture.md) — How PyDepot works internally
