# Architecture

## Overview

DepotPy is structured as a pipeline that transforms a Python project into a self-contained offline installation bundle:

```
Project Directory → Detect → Resolve → Download → Manifest → Pack → .tar.gz
```

## Module Map

```
src/depotpy/
├── __init__.py        # Public API exports
├── cli.py             # argparse entry point, subcommand dispatch
├── commands/
│   ├── pack.py        # pack subcommand handler
│   ├── inspect.py     # inspect subcommand handler + BundleInspector
│   └── install.py     # install subcommand handler
├── detector.py        # Dependency manager detection + project metadata extraction
├── models.py          # Data models (dataclasses + enums)
├── platforms.py       # Platform tags, presets, and resolution
├── resolver.py        # Dependency download via pip/uv
├── manifest.py        # manifest.json serialization/deserialization
├── packer.py          # tar.gz bundle creation + PackBuilder
└── installer.py       # Bundle extraction and pip install
```

## Data Flow

### Pack Pipeline

```
1. CLI (cli.py)
   ↓ parse args → PackOptions
2. PackBuilder (packer.py)
   ↓ orchestrates the pipeline
3. detect_project (detector.py)
   ↓ scan project files → ProjectInfo
4. resolve_platforms (platforms.py)
   ↓ parse --platform args → list[PlatformTag]
5. download_packages (resolver.py)
   ↓ pip/uv download → list[PackageFile]
6. Manifest (models.py)
   ↓ assemble metadata
7. _create_bundle_tarball (packer.py)
   ↓ tar.gz with README + manifest + packages
8. Output: {name}-{version}-offline.tar.gz
```

### Inspect Pipeline

```
1. CLI → BundleInspector
2. Open tar.gz, find manifest.json
3. Parse manifest → Manifest object
4. Print summary
```

### Install Pipeline

```
1. CLI → BundleInstaller
2. Extract tar.gz to temp directory
3. Find manifest.json → get package names
4. Run: pip install --no-index --find-links ./packages <names>
5. Clean up temp directory
```

## Key Design Decisions

### No Runtime Dependencies

DepotPy uses only the Python standard library. External tools (uv, poetry, pdm, pip) are invoked via `subprocess` and are detected at runtime, not declared as package dependencies. This makes DepotPy easy to install in constrained environments.

### Dependency Manager Detection

Detection follows a strict priority order (uv > poetry > pdm > pipenv > pip). Each manager is checked via two signals:

1. **Lock file presence** — `uv.lock`, `poetry.lock`, etc.
2. **Tool section in pyproject.toml** — `[tool.uv]`, `[tool.poetry]`, etc.

If a manager is detected but its CLI is not installed (`shutil.which` returns None), DepotPy falls back to the next option, ultimately reaching pip.

### Platform Tags

Platform tags follow the [PEP 425](https://peps.python.org/pep-0425/) wheel compatibility tag scheme. DepotPy defines 8 common platform tags grouped into presets (`all`, `linux`, `macos`, `windows`).

When `--platform` is not specified, only the current platform is used. This is deliberate — cross-platform bundles are significantly larger and most users only need their own platform.

### Download Strategy

For each platform, DepotPy runs a separate `pip download` (or `uv pip download`) command with `--platform` and `--only-binary=:all:`. This ensures platform-specific binary wheels are fetched correctly.

Files are downloaded into a single flat directory. Duplicate filenames (e.g. the same pure-Python wheel downloaded for multiple platforms) are naturally deduplicated by the filesystem.

### Bundle Format

The `.tar.gz` format was chosen for:

- Universal support — every OS can extract it
- Compression — smaller than zip for typical wheel contents
- Streaming — can be created without seeking
- Simplicity — no custom format, just standard tar

The top-level directory inside the tar ensures safe extraction (no file scattering).

### Manifest Design

`manifest.json` serves two purposes:

1. **Machine-readable**: Programs can parse it to verify bundle contents
2. **Integrity**: SHA-256 hashes enable verification of individual package files

The manifest is not used during manual pip installation — it's an optional metadata layer.

## Error Handling Strategy

Errors are classified into three categories:

| Exception | Meaning | Example |
|-----------|---------|---------|
| `FileNotFoundError` | Input doesn't exist | Project path or bundle file missing |
| `ValueError` | Invalid input | No project config found, no manifest in bundle |
| `RuntimeError` | External tool failure | pip download or install failed |

Each CLI subcommand catches these and prints user-friendly error messages to stderr, returning exit code 1.

## Testing Strategy

Tests are organized to mirror the source structure:

```
tests/
├── test_cli.py            # CLI parsing and dispatch
├── test_platforms.py       # Platform tags and resolution
├── test_models.py          # Data model behavior
├── test_detector.py        # Dependency manager detection
├── test_resolver.py        # Download command building and file scanning
├── test_manifest.py        # Manifest serialization roundtrips
├── test_packer.py          # Bundle creation
├── test_inspect.py         # Inspect subcommand
├── test_installer.py       # Install subcommand
└── test_pack_command.py    # Pack subcommand handler
```

External tool invocations (`pip download`, `pip install`) are mocked at the `subprocess.run` level. File system operations use pytest's `tmp_path` fixture.
