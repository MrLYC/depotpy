# Python API Reference

DepotPy exposes three main classes for programmatic use:

```python
from depotpy import PackBuilder, BundleInspector, BundleInstaller
```

## PackBuilder

Builds an offline installation bundle from a Python project.

### Constructor

```python
from depotpy.packer import PackBuilder
from depotpy.models import PackOptions, PackagePreference
from pathlib import Path

options = PackOptions(
    project_path=Path("/path/to/project"),
    output_dir=Path("/output"),
    platforms=["manylinux2014_x86_64", "macosx_11_0_arm64"],
    python_version="3.11",
    exclude=["pytest"],
    include_extras=["dev"],
    prefer=PackagePreference.WHEEL,
)
builder = PackBuilder(options)
```

### Methods

#### `build() -> tuple[Path, Manifest]`

Execute the full build pipeline: detect project, resolve dependencies, download wheels, generate manifest, and create the tar.gz bundle.

**Returns**: Tuple of (path to the created `.tar.gz` file, Manifest object).

**Raises**:
- `FileNotFoundError` — project path does not exist
- `ValueError` — project configuration cannot be detected
- `RuntimeError` — dependency download fails

```python
bundle_path, manifest = builder.build()
print(f"Bundle created at: {bundle_path}")
print(f"Total packages: {manifest.package_count}")
```

---

## BundleInspector

Inspect the contents of an offline bundle.

### Constructor

```python
from depotpy.commands.inspect import BundleInspector
from pathlib import Path

inspector = BundleInspector(Path("myapp-1.0.0-offline.tar.gz"))
```

### Methods

#### `get_manifest() -> dict`

Extract and return the raw manifest data from the bundle.

**Returns**: Dictionary with manifest contents.

**Raises**:
- `FileNotFoundError` — bundle file does not exist
- `ValueError` — bundle does not contain a manifest.json

```python
data = inspector.get_manifest()
print(data["project_name"])    # "myapp"
print(data["packages"])        # list of package dicts
```

#### `print_summary() -> None`

Print a human-readable summary to stderr.

```python
inspector.print_summary()
```

---

## BundleInstaller

Install packages from an offline bundle.

### Constructor

```python
from depotpy.installer import BundleInstaller
from pathlib import Path

installer = BundleInstaller(Path("myapp-1.0.0-offline.tar.gz"))
```

### Methods

#### `install(target: str | None = None, on_conflict: ConflictPolicy = ConflictPolicy.KEEP) -> None`

Extract the bundle and install packages using pip.

**Parameters**:
- `target` — Optional directory to install into (pip `--target`)
- `on_conflict` — How to handle conflicts with installed packages (see `ConflictPolicy`)

**Raises**:
- `FileNotFoundError` — bundle file does not exist
- `ValueError` — bundle has no manifest
- `RuntimeError` — pip install fails, or conflicts detected with `ConflictPolicy.ERROR`

```python
from depotpy.models import ConflictPolicy

# Install into current environment
installer.install()

# Install into specific directory
installer.install(target="/opt/myapp/lib")

# Force reinstall all packages
installer.install(on_conflict=ConflictPolicy.OVERWRITE)

# Abort on version conflicts
installer.install(on_conflict=ConflictPolicy.ERROR)
```

---

## Data Models

### PackOptions

Options for the pack command.

```python
from depotpy.models import PackOptions, PackagePreference
from pathlib import Path

options = PackOptions(
    project_path=Path("."),        # Required: project root
    output_dir=Path("./dist"),     # Required: output directory
    platforms=[],                  # Optional: platform tags or presets
    python_version=None,           # Optional: override Python version
    exclude=[],                    # Optional: dependencies to exclude
    include_extras=[],             # Optional: extras to include
    prefer=PackagePreference.WHEEL,  # Optional: wheel or source preference
)
```

### ProjectInfo

Detected project metadata. Returned by `detect_project()`.

```python
from depotpy.detector import detect_project
from pathlib import Path

info = detect_project(Path("/path/to/project"))
print(info.name)              # "myapp"
print(info.version)           # "1.0.0"
print(info.dependencies)      # ["requests>=2.0", "click"]
print(info.extras)            # {"dev": ["pytest"]}
print(info.manager)           # DependencyManager.UV
print(info.python_requires)   # ">=3.11"
```

### PackageFile

Represents a downloaded package file.

```python
from depotpy.models import PackageFile

pkg = PackageFile(
    filename="requests-2.31.0-py3-none-any.whl",
    name="requests",
    version="2.31.0",
    sha256="abc123...",
    size=62000,
    platform_tags=[],
)

pkg.is_wheel    # True
pkg.is_sdist    # False
```

### Manifest

The manifest.json content.

```python
from depotpy.models import Manifest

manifest = Manifest(
    project_name="myapp",
    project_version="1.0.0",
    python_version="3.11",
    platforms=["manylinux2014_x86_64"],
    packages=[...],               # list of PackageFile
)

manifest.package_count    # number of packages
manifest.total_size       # total size in bytes
```

### DependencyManager

Enum of supported dependency managers.

```python
from depotpy.models import DependencyManager

DependencyManager.UV        # "uv"
DependencyManager.POETRY    # "poetry"
DependencyManager.PDM       # "pdm"
DependencyManager.PIPENV    # "pipenv"
DependencyManager.PIP       # "pip"
```

### PackagePreference

Enum for package format preference.

```python
from depotpy.models import PackagePreference

PackagePreference.WHEEL     # "wheel" — prefer pre-built wheels (default)
PackagePreference.SOURCE    # "source" — prefer source distributions
```

### ConflictPolicy

Enum for handling conflicts with installed packages.

```python
from depotpy.models import ConflictPolicy

ConflictPolicy.KEEP         # "keep" — keep existing, skip conflicts (default)
ConflictPolicy.OVERWRITE    # "overwrite" — force reinstall from bundle
ConflictPolicy.ERROR        # "error" — abort if conflicts detected
```

---

## Utility Functions

### Platform Resolution

```python
from depotpy.platforms import resolve_platforms, get_current_platform

# Get current platform
current = get_current_platform()
print(current.tag)    # e.g. "manylinux2014_x86_64"

# Resolve platform arguments
platforms = resolve_platforms(["linux", "macosx_11_0_arm64"])
# Returns: [MANYLINUX_X86_64, MANYLINUX_AARCH64, MUSLLINUX_X86_64, MUSLLINUX_AARCH64, MACOSX_ARM64]
```

### Manifest I/O

```python
from depotpy.manifest import write_manifest, read_manifest

# Write
write_manifest(manifest, Path("manifest.json"))

# Read
manifest = read_manifest(Path("manifest.json"))
```

### Dependency Detection

```python
from depotpy.detector import detect_project
from pathlib import Path

info = detect_project(Path("/path/to/project"))
```
