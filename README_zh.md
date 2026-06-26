# PyDepot

中文 | [English](README.md)

为 Python 项目构建可跨平台分发的离线安装包。

PyDepot 分析项目依赖，为多个平台下载 wheels，将所有内容打包为 `.tar.gz` 归档文件，其中包含清单文件和安装说明。生成的离线包可以传输到无网络环境中，通过一条 `pip` 命令即可完成安装。

## 特性

- **跨平台**: 一次性下载 Linux、macOS、Windows 多平台的 wheels
- **自动检测**: 自动识别项目使用的依赖管理工具（uv、poetry、pdm、pipenv、pip）
- **离线可用**: 生成的离线包无需任何网络连接即可安装
- **可验证**: manifest.json 中包含 SHA-256 哈希，用于完整性校验
- **库级 API**: 既可作为 CLI 工具使用，也可作为 Python 库导入

## 安装

```bash
pip install pydepot
```

## 快速开始

```bash
# 为当前平台构建离线包
pydepot pack /path/to/your/project

# 为多个平台构建
pydepot pack /path/to/project --platform manylinux2014_x86_64 --platform macosx_11_0_arm64

# 为所有支持的平台构建
pydepot pack /path/to/project --platform all

# 查看离线包内容
pydepot inspect myapp-1.0.0-offline.tar.gz

# 从离线包安装（在目标机器上执行）
pydepot install myapp-1.0.0-offline.tar.gz
```

## 文档

| 中文 | English |
|------|---------|
| [快速上手](docs/zh/getting-started.md) | [Getting Started](docs/en/getting-started.md) |
| [CLI 参考](docs/zh/cli-reference.md) | [CLI Reference](docs/en/cli-reference.md) |
| [Python API 参考](docs/zh/api-reference.md) | [Python API Reference](docs/en/api-reference.md) |
| [架构设计](docs/zh/architecture.md) | [Architecture](docs/en/architecture.md) |
| [贡献指南](docs/zh/contributing.md) | [Contributing](docs/en/contributing.md) |

## 许可证

MIT
