# PyDepot

Build cross-platform offline installation packages for Python projects.

PyDepot analyzes your project's dependencies, downloads wheels for multiple platforms, and bundles everything into a `.tar.gz` archive with a manifest and installation instructions. The resulting bundle can be transferred to offline environments and installed with a single `pip` command.

## Installation

```bash
pip install pydepot
```

## Quick Start

```bash
# Build an offline bundle for the current platform
pydepot pack /path/to/your/project

# Build for multiple platforms
pydepot pack /path/to/project --platform manylinux2014_x86_64 --platform macosx_11_0_arm64

# Build for all supported platforms
pydepot pack /path/to/project --platform all

# Inspect a bundle
pydepot inspect myapp-1.0.0-offline.tar.gz

# Install from a bundle (on the target machine)
pydepot install myapp-1.0.0-offline.tar.gz
```

## CLI Reference

### `pydepot pack <project_path>`

Build an offline installation package.

| Option | Description |
|--------|-------------|
| `-o, --output` | Output directory (default: current directory) |
| `--platform` | Target platform, repeatable. Use `all` for all platforms |
| `--python-version` | Override Python version (e.g. `3.11`) |
| `--exclude` | Exclude a dependency, repeatable |
| `--include-extras` | Include extras dependencies, repeatable |

### `pydepot inspect <bundle_path>`

Display the contents and metadata of an offline bundle.

### `pydepot install <bundle_path>`

Install packages from an offline bundle into the current environment.

| Option | Description |
|--------|-------------|
| `--target` | Install into the specified directory |

## Bundle Structure

```
myapp-1.0.0-offline/
  README.md          # Installation instructions
  manifest.json      # Package manifest with versions and hashes
  packages/          # All .whl and .tar.gz files
```

To install manually without PyDepot:

```bash
tar xzf myapp-1.0.0-offline.tar.gz
cd myapp-1.0.0-offline
pip install --no-index --find-links ./packages <package-names>
```

## Dependency Manager Detection

PyDepot auto-detects and uses your project's dependency manager:

| Priority | Manager | Detection |
|----------|---------|-----------|
| 1 | uv | `uv.lock` or `[tool.uv]` in pyproject.toml |
| 2 | poetry | `poetry.lock` or `[tool.poetry]` in pyproject.toml |
| 3 | pdm | `pdm.lock` or `[tool.pdm]` in pyproject.toml |
| 4 | pipenv | `Pipfile` or `Pipfile.lock` |
| 5 | pip | `requirements.txt`, `setup.py`, `setup.cfg` |

If the detected tool is not installed, PyDepot falls back to pip.

## Supported Platforms

| Preset | Platforms |
|--------|-----------|
| `linux` | manylinux2014_x86_64, manylinux2014_aarch64, musllinux_1_2_x86_64, musllinux_1_2_aarch64 |
| `macos` | macosx_11_0_x86_64, macosx_11_0_arm64 |
| `windows` | win_amd64, win_arm64 |
| `all` | All of the above |

## Python API

```python
from pydepot import PackBuilder, BundleInspector, BundleInstaller
from pydepot.models import PackOptions
from pathlib import Path

# Build a bundle
options = PackOptions(
    project_path=Path("/path/to/project"),
    output_dir=Path("/output"),
    platforms=["manylinux2014_x86_64", "macosx_11_0_arm64"],
)
builder = PackBuilder(options)
bundle_path = builder.build()

# Inspect a bundle
inspector = BundleInspector(bundle_path)
inspector.print_summary()

# Install from a bundle
installer = BundleInstaller(bundle_path)
installer.install()
```

## License

MIT
