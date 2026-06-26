# 快速上手

## 环境要求

- Python 3.11 或更高版本
- pip（Python 自带）
- 可选：[uv](https://github.com/astral-sh/uv)、[poetry](https://python-poetry.org/)、[pdm](https://pdm-project.org/) 或 [pipenv](https://pipenv.pypa.io/) — 如果你的项目使用了这些工具，DepotPy 会自动识别并使用

## 安装

```bash
pip install depotpy
```

验证安装：

```bash
depotpy --version
```

## 创建你的第一个离线包

### 1. 打包

进入任何包含 `pyproject.toml`、`setup.cfg` 或 `requirements.txt` 的 Python 项目目录，然后运行：

```bash
depotpy pack .
```

这个命令会：
1. 自动检测你的依赖管理工具和项目元数据
2. 下载当前平台的所有依赖 wheels
3. 生成包含版本号和 SHA-256 哈希的 `manifest.json`
4. 在当前目录创建 `.tar.gz` 离线包

输出文件名为 `{项目名}-{版本号}-offline.tar.gz`。

### 2. 传输

通过 USB、SCP 或其他方式将 `.tar.gz` 文件复制到目标机器：

```bash
scp myapp-1.0.0-offline.tar.gz user@target-host:/tmp/
```

### 3. 安装

在目标机器上（无需网络连接）：

```bash
# 使用 DepotPy（如果已安装）
depotpy install myapp-1.0.0-offline.tar.gz

# 或者手动安装
tar xzf myapp-1.0.0-offline.tar.gz
cd myapp-1.0.0-offline
pip install --no-index --find-links ./packages <包名列表>
```

离线包中的 `README.md` 里已经包含了完整的 `pip install` 命令。

## 跨平台打包

构建一个包含多个平台 wheels 的离线包：

```bash
# 指定具体平台
depotpy pack . --platform manylinux2014_x86_64 --platform macosx_11_0_arm64

# 使用预设
depotpy pack . --platform linux    # 所有 Linux 变体
depotpy pack . --platform macos    # macOS x86_64 + ARM
depotpy pack . --platform all      # 全部 8 个平台
```

跨平台离线包体积较大，因为包含了每个目标平台的专用 wheels。纯 Python wheels（如 `requests`）只会包含一份。

## 查看离线包内容

传输之前，可以先确认离线包的内容：

```bash
depotpy inspect myapp-1.0.0-offline.tar.gz
```

输出示例：
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

## 常用选项

```bash
# 覆盖 Python 版本
depotpy pack . --python-version 3.12

# 排除特定依赖
depotpy pack . --exclude pytest --exclude mypy

# 包含可选 extras
depotpy pack . --include-extras dev --include-extras docs

# 指定输出目录
depotpy pack . -o /path/to/output/
```

## 下一步

- [CLI 参考](cli-reference.md) — 完整的命令行文档
- [Python API 参考](api-reference.md) — 将 DepotPy 作为库使用
- [架构设计](architecture.md) — DepotPy 的内部工作原理
