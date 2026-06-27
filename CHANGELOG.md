# Changelog / 变更日志

All notable changes to this project will be documented in this file.
本文件记录项目的所有重要变更。

The format is based on [Keep a Changelog](https://keepachangelog.com/).
格式基于 [Keep a Changelog](https://keepachangelog.com/)。

## [1.0.0] - 2026-06-27

First stable (GA) release.
首个稳定 (GA) 版本。

### Added / 新增
- **`--dry-run` flag**: Preview dependencies and target platforms without downloading.
  **`--dry-run` 标志**：预览依赖和目标平台，不实际下载。
- **`-v/--verbose` and `-q/--quiet` flags**: Control logging verbosity (debug / info / warning).
  **`-v/--verbose` 和 `-q/--quiet` 标志**：控制日志详细程度（调试/信息/警告）。
- **Parallel downloads**: Multi-platform downloads run concurrently (up to 4 workers).
  **并行下载**：多平台下载并发执行（最多 4 个工作线程）。
- **Download progress**: Log `[1/N] Completed download for ...` per platform.
  **下载进度**：每个平台显示 `[1/N] Completed download for ...` 日志。
- `py.typed` marker for PEP 561 type checking support.
  `py.typed` 标记，支持 PEP 561 类型检查。
- `LICENSE` file (MIT).
  `LICENSE` 文件 (MIT)。
- `SECURITY.md` security disclosure policy.
  `SECURITY.md` 安全披露策略。
- `CHANGELOG.md` (this file).
  `CHANGELOG.md`（本文件）。
- mypy type checking in CI pipeline.
  CI 流水线中的 mypy 类型检查。

### Fixed / 修复
- **Wheel filename parsing**: Correctly handle hyphenated package names (e.g. `my-cool-pkg`) and build tags by parsing from the right per PEP 427.
  **Wheel 文件名解析**：按 PEP 427 从右侧解析，正确处理含连字符的包名（如 `my-cool-pkg`）和 build tag。
- **requirements.txt parsing**: Skip pip options (`--index-url`, `-f`, `-e`, etc.) and strip inline comments.
  **requirements.txt 解析**：跳过 pip 选项（`--index-url`、`-f`、`-e` 等）并去除行内注释。
- **Installer error handling**: Distinguish pip-not-found vs pip-failed vs invalid-JSON instead of silently returning empty results.
  **安装器错误处理**：区分 pip 不存在、pip 执行失败和 JSON 解析错误，不再静默返回空结果。
- **Tarball path sanitization**: Prevent path traversal in archive filenames.
  **Tarball 路径清理**：防止归档文件名中的路径穿越。
- **TOML error handling**: Gracefully handle malformed `pyproject.toml` files.
  **TOML 错误处理**：优雅处理格式错误的 `pyproject.toml` 文件。

### Changed / 变更
- Deduplicated pip/uv download command building into shared functions.
  将 pip/uv 下载命令构建提取为共享函数，消除重复代码。
- Dependency name extraction now uses PEP 508 regex instead of fragile string splits.
  依赖名提取现在使用 PEP 508 正则表达式，取代脆弱的字符串分割。
- Development status classifier changed from `Alpha` to `Production/Stable`.
  开发状态分类器从 `Alpha` 更改为 `Production/Stable`。
- Added `[project.urls]` to `pyproject.toml` for PyPI project links.
  在 `pyproject.toml` 中添加 `[project.urls]`，在 PyPI 上显示项目链接。

## [0.3.0] - 2026-06-27

### Added / 新增
- `[project.urls]` in `pyproject.toml` for PyPI project links.
  `pyproject.toml` 中添加 `[project.urls]`，用于 PyPI 项目链接。

## [0.2.0] - 2026-06-27

### Added / 新增
- `--json` flag for all commands (pack, inspect, install).
  所有命令（pack、inspect、install）的 `--json` 标志。
- `--on-conflict` flag for install command (`keep`, `overwrite`, `error`).
  install 命令的 `--on-conflict` 标志（`keep`、`overwrite`、`error`）。
- `--prefer` flag for pack command (`wheel`, `source`).
  pack 命令的 `--prefer` 标志（`wheel`、`source`）。
- Architecture documentation.
  架构设计文档。

## [0.1.1] - 2026-06-27

### Fixed / 修复
- Project renaming from PyDepot to DepotPy.
  项目从 PyDepot 重命名为 DepotPy。

## [0.1.0] - 2026-06-27

Initial release.
首次发布。

### Added / 新增
- `depotpy pack` command for building offline bundles.
  `depotpy pack` 命令，用于构建离线安装包。
- `depotpy inspect` command for inspecting bundles.
  `depotpy inspect` 命令，用于查看离线包内容。
- `depotpy install` command for installing from bundles.
  `depotpy install` 命令，用于从离线包安装。
- Auto-detection for uv, poetry, pdm, pipenv, pip.
  自动检测 uv、poetry、pdm、pipenv、pip。
- Cross-platform support with 8 platform tags and 4 presets.
  跨平台支持，8 个平台标签和 4 个预设。
- SHA-256 integrity verification in manifest.
  manifest 中的 SHA-256 完整性校验。
- Python library API (`PackBuilder`, `BundleInspector`, `BundleInstaller`).
  Python 库 API（`PackBuilder`、`BundleInspector`、`BundleInstaller`）。
