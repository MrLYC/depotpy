# CLI Reference

## Global Options

```bash
depotpy --version    # Show version
depotpy --help       # Show help
depotpy -h           # Show help (short form)
depotpy -v ...       # Enable verbose (debug) output
depotpy -q ...       # Suppress informational output (warnings and errors only)
```

| Option | Description |
|--------|-------------|
| `--version` | Show version and exit |
| `-h, --help` | Show help and exit |
| `-v, --verbose` | Enable verbose (debug) output |
| `-q, --quiet` | Suppress informational output (warnings and errors only) |

## `depotpy pack`

Build an offline installation package from a Python project.

```bash
depotpy pack <project_path> [options]
```

### Arguments

| Argument | Description |
|----------|-------------|
| `project_path` | Path to the Python project root directory |

### Options

| Option | Description | Default |
|--------|-------------|---------|
| `-o, --output DIR` | Output directory for the bundle | `.` (current directory) |
| `--platform PLATFORM` | Target platform tag or preset. Can be specified multiple times | Current platform |
| `--python-version VER` | Override Python version (e.g. `3.11`, `3.12`) | Current Python version |
| `--exclude PKG` | Exclude a dependency by name. Can be specified multiple times | None |
| `--include-extras EXTRA` | Include an extras group. Can be specified multiple times | None |
| `--prefer {wheel,source}` | Prefer wheel or source packages | `wheel` |
| `--dry-run` | Show what would be downloaded without actually downloading | Off |
| `--json` | Output result as JSON to stdout | Off |

### Platform Values

Individual platform tags:

| Tag | OS | Architecture |
|-----|----|-------------|
| `manylinux2014_x86_64` | Linux (glibc) | x86_64 |
| `manylinux2014_aarch64` | Linux (glibc) | ARM64 |
| `musllinux_1_2_x86_64` | Linux (musl) | x86_64 |
| `musllinux_1_2_aarch64` | Linux (musl) | ARM64 |
| `macosx_11_0_x86_64` | macOS | Intel |
| `macosx_11_0_arm64` | macOS | Apple Silicon |
| `win_amd64` | Windows | x86_64 |
| `win_arm64` | Windows | ARM64 |

Presets:

| Preset | Includes |
|--------|----------|
| `all` | All 8 platforms |
| `linux` | All 4 Linux variants |
| `macos` | Both macOS architectures |
| `windows` | Both Windows architectures |

### Examples

```bash
# Pack for current platform
depotpy pack /path/to/project

# Pack for specific platforms
depotpy pack . --platform manylinux2014_x86_64 --platform macosx_11_0_arm64

# Pack for all platforms with extras
depotpy pack . --platform all --include-extras dev

# Pack excluding test dependencies
depotpy pack . --exclude pytest --exclude coverage

# Pack with custom output and Python version
depotpy pack . -o ./dist --python-version 3.12

# Prefer source distributions
depotpy pack . --prefer source

# Preview what would be downloaded (dry run)
depotpy pack . --platform all --dry-run

# Machine-readable JSON output
depotpy pack . --json

# Verbose output for debugging
depotpy -v pack .

# Quiet mode for scripts
depotpy -q pack . --json
```

### Output

Creates a file named `{project_name}-{version}-offline.tar.gz` in the output directory.

The bundle contains:

```
{project_name}-{version}-offline/
  README.md          # Installation instructions with exact pip command
  manifest.json      # Package manifest (names, versions, SHA-256 hashes)
  packages/          # All .whl and .tar.gz files
```

---

## `depotpy inspect`

Display the contents and metadata of an offline bundle.

```bash
depotpy inspect <bundle_path> [options]
```

### Arguments

| Argument | Description |
|----------|-------------|
| `bundle_path` | Path to the `.tar.gz` bundle file |

### Options

| Option | Description | Default |
|--------|-------------|---------|
| `--json` | Output result as JSON to stdout | Off |

### Examples

```bash
depotpy inspect myapp-1.0.0-offline.tar.gz

# Machine-readable output
depotpy inspect myapp-1.0.0-offline.tar.gz --json
```

### Output

```
Bundle: myapp-1.0.0-offline.tar.gz
Project: myapp 1.0.0
Python: 3.11
Platforms: manylinux2014_x86_64, macosx_11_0_arm64
Packages: 12
Total size: 8.5 MB

Package list:
  certifi 2024.2.2 (wheel, any, 157 KB)
  numpy 1.26.4 (wheel, manylinux2014_x86_64, 18132 KB)
  ...
```

---

## `depotpy install`

Install packages from an offline bundle into the current Python environment.

```bash
depotpy install <bundle_path> [options]
```

### Arguments

| Argument | Description |
|----------|-------------|
| `bundle_path` | Path to the `.tar.gz` bundle file |

### Options

| Option | Description | Default |
|--------|-------------|---------|
| `--target DIR` | Install packages into a specific directory | Current environment |
| `--on-conflict {keep,overwrite,error}` | How to handle conflicts with installed packages | `keep` |
| `--json` | Output result as JSON to stdout | Off |

The `--on-conflict` policies:

| Policy | Behavior |
|--------|----------|
| `keep` | Keep existing installed versions, skip conflicting packages |
| `overwrite` | Force reinstall all packages from the bundle |
| `error` | Abort with an error if any version conflicts are detected |

### Examples

```bash
# Install into current environment
depotpy install myapp-1.0.0-offline.tar.gz

# Install into a specific directory
depotpy install myapp-1.0.0-offline.tar.gz --target /opt/myapp/lib

# Force reinstall all packages
depotpy install myapp-1.0.0-offline.tar.gz --on-conflict overwrite

# Fail if there are version conflicts
depotpy install myapp-1.0.0-offline.tar.gz --on-conflict error

# Machine-readable output
depotpy install myapp-1.0.0-offline.tar.gz --json
```

### Manual Installation

You don't need DepotPy installed on the target machine. Extract and use pip directly:

```bash
tar xzf myapp-1.0.0-offline.tar.gz
cd myapp-1.0.0-offline
pip install --no-index --find-links ./packages <package-names>
```

The exact command with all package names is in the bundle's `README.md`.

---

## Exit Codes

| Code | Meaning |
|------|---------|
| `0` | Success |
| `1` | Error (file not found, invalid project, download failure, etc.) |

## Dependency Manager Detection

DepotPy automatically detects which dependency manager your project uses:

| Priority | Manager | Detected By | Command Used |
|----------|---------|-------------|--------------|
| 1 | uv | `uv.lock` or `[tool.uv]` | `uv pip download` |
| 2 | poetry | `poetry.lock` or `[tool.poetry]` | Falls back to pip |
| 3 | pdm | `pdm.lock` or `[tool.pdm]` | Falls back to pip |
| 4 | pipenv | `Pipfile` or `Pipfile.lock` | Falls back to pip |
| 5 | pip | `requirements.txt`, `setup.py`, `setup.cfg` | `pip download` |

If the detected tool is not installed on the system, DepotPy automatically falls back to pip for downloading.
