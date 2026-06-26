# CLI Reference

## Global Options

```bash
pydepot --version    # Show version
pydepot --help       # Show help
pydepot -h           # Show help (short form)
```

## `pydepot pack`

Build an offline installation package from a Python project.

```bash
pydepot pack <project_path> [options]
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
pydepot pack /path/to/project

# Pack for specific platforms
pydepot pack . --platform manylinux2014_x86_64 --platform macosx_11_0_arm64

# Pack for all platforms with extras
pydepot pack . --platform all --include-extras dev

# Pack excluding test dependencies
pydepot pack . --exclude pytest --exclude coverage

# Pack with custom output and Python version
pydepot pack . -o ./dist --python-version 3.12
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

## `pydepot inspect`

Display the contents and metadata of an offline bundle.

```bash
pydepot inspect <bundle_path>
```

### Arguments

| Argument | Description |
|----------|-------------|
| `bundle_path` | Path to the `.tar.gz` bundle file |

### Examples

```bash
pydepot inspect myapp-1.0.0-offline.tar.gz
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

## `pydepot install`

Install packages from an offline bundle into the current Python environment.

```bash
pydepot install <bundle_path> [options]
```

### Arguments

| Argument | Description |
|----------|-------------|
| `bundle_path` | Path to the `.tar.gz` bundle file |

### Options

| Option | Description | Default |
|--------|-------------|---------|
| `--target DIR` | Install packages into a specific directory | Current environment |

### Examples

```bash
# Install into current environment
pydepot install myapp-1.0.0-offline.tar.gz

# Install into a specific directory
pydepot install myapp-1.0.0-offline.tar.gz --target /opt/myapp/lib
```

### Manual Installation

You don't need PyDepot installed on the target machine. Extract and use pip directly:

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

PyDepot automatically detects which dependency manager your project uses:

| Priority | Manager | Detected By | Command Used |
|----------|---------|-------------|--------------|
| 1 | uv | `uv.lock` or `[tool.uv]` | `uv pip download` |
| 2 | poetry | `poetry.lock` or `[tool.poetry]` | Falls back to pip |
| 3 | pdm | `pdm.lock` or `[tool.pdm]` | Falls back to pip |
| 4 | pipenv | `Pipfile` or `Pipfile.lock` | Falls back to pip |
| 5 | pip | `requirements.txt`, `setup.py`, `setup.cfg` | `pip download` |

If the detected tool is not installed on the system, PyDepot automatically falls back to pip for downloading.
