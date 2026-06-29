# DepotPy

[中文文档](https://github.com/MrLYC/depotpy/blob/main/README_zh.md) | English

Build cross-platform offline installation packages for Python projects.

DepotPy analyzes your project's dependencies, downloads wheels for multiple platforms, and bundles them into a `.tar.gz` dependency archive with a manifest and installation instructions. The resulting bundle can be transferred to offline environments and installed with DepotPy or pip.

## Features

- **Cross-platform**: Download wheels for Linux, macOS, and Windows in one go
- **Auto-detection**: Automatically detects your dependency manager (uv, poetry, pdm, pipenv, pip)
- **Offline-ready**: Generated dependency bundles work without network access when compatible wheels are available
- **Verified install**: `depotpy install` checks manifest SHA-256 hashes and file sizes before invoking pip
- **Library API**: Use as a CLI tool or import as a Python library

## Installation

```bash
pip install depotpy
```

Verify the install and active Python environment:

```bash
python -m depotpy --version
```

## Quick Start

```bash
# Build an offline bundle for the current platform
depotpy pack /path/to/your/project

# Build for multiple platforms
depotpy pack /path/to/project --platform manylinux2014_x86_64 --platform macosx_11_0_arm64

# Build for all supported platforms
depotpy pack /path/to/project --platform all

# Inspect a bundle
depotpy inspect myapp-1.0.0-offline.tar.gz

# Install from a bundle (on the target machine)
depotpy install myapp-1.0.0-offline.tar.gz
```

## Architecture

DepotPy is organized as a small standard-library-only CLI pipeline:

```text
project metadata -> dependency download -> manifest + packages -> offline bundle -> verified install
```

- `depotpy.cli` parses `pack`, `inspect`, and `install`, then dispatches to the command modules.
- `PackBuilder` orchestrates project detection, platform resolution, package download, manifest generation, and tarball creation.
- The offline bundle contains `manifest.json`, `packages/`, and a generated `README.md`.
- `inspect` reads `manifest.json` from an existing bundle, while `install` verifies package hashes/sizes and invokes the current interpreter's pip with local package files.

## Documentation

| English | Chinese |
|---------|---------|
| [Getting Started](https://github.com/MrLYC/depotpy/blob/main/docs/en/getting-started.md) | [快速上手](https://github.com/MrLYC/depotpy/blob/main/docs/zh/getting-started.md) |
| [CLI Reference](https://github.com/MrLYC/depotpy/blob/main/docs/en/cli-reference.md) | [CLI 参考](https://github.com/MrLYC/depotpy/blob/main/docs/zh/cli-reference.md) |
| [Python API Reference](https://github.com/MrLYC/depotpy/blob/main/docs/en/api-reference.md) | [Python API 参考](https://github.com/MrLYC/depotpy/blob/main/docs/zh/api-reference.md) |
| [Architecture](https://github.com/MrLYC/depotpy/blob/main/docs/en/architecture.md) | [架构设计](https://github.com/MrLYC/depotpy/blob/main/docs/zh/architecture.md) |
| [Contributing](https://github.com/MrLYC/depotpy/blob/main/docs/en/contributing.md) | [贡献指南](https://github.com/MrLYC/depotpy/blob/main/docs/zh/contributing.md) |

## License

MIT
