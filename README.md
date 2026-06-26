# PyDepot

[中文文档](README_zh.md) | English

Build cross-platform offline installation packages for Python projects.

PyDepot analyzes your project's dependencies, downloads wheels for multiple platforms, and bundles everything into a `.tar.gz` archive with a manifest and installation instructions. The resulting bundle can be transferred to offline environments and installed with a single `pip` command.

## Features

- **Cross-platform**: Download wheels for Linux, macOS, and Windows in one go
- **Auto-detection**: Automatically detects your dependency manager (uv, poetry, pdm, pipenv, pip)
- **Offline-ready**: Generated bundles work without any network access
- **Verifiable**: SHA-256 hashes in manifest.json for integrity checks
- **Library API**: Use as a CLI tool or import as a Python library

## Installation

```bash
pip install depotpy
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

## Documentation

| English | Chinese |
|---------|---------|
| [Getting Started](docs/en/getting-started.md) | [快速上手](docs/zh/getting-started.md) |
| [CLI Reference](docs/en/cli-reference.md) | [CLI 参考](docs/zh/cli-reference.md) |
| [Python API Reference](docs/en/api-reference.md) | [Python API 参考](docs/zh/api-reference.md) |
| [Architecture](docs/en/architecture.md) | [架构设计](docs/zh/architecture.md) |
| [Contributing](docs/en/contributing.md) | [贡献指南](docs/zh/contributing.md) |

## License

MIT
