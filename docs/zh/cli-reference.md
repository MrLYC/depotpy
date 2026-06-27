# CLI 参考

## 全局选项

```bash
depotpy --version    # 显示版本号
depotpy --help       # 显示帮助信息
depotpy -h           # 显示帮助信息（短格式）
depotpy -v ...       # 启用详细（调试）输出
depotpy -q ...       # 静默模式，仅显示警告和错误
```

| 选项 | 说明 |
|------|------|
| `--version` | 显示版本号并退出 |
| `-h, --help` | 显示帮助信息并退出 |
| `-v, --verbose` | 启用详细（调试）输出 |
| `-q, --quiet` | 静默模式，仅显示警告和错误 |

## `depotpy pack`

从 Python 项目构建离线安装包。

```bash
depotpy pack <project_path> [选项]
```

### 参数

| 参数 | 说明 |
|------|------|
| `project_path` | Python 项目根目录路径 |

### 选项

| 选项 | 说明 | 默认值 |
|------|------|--------|
| `-o, --output DIR` | 输出目录 | `.`（当前目录） |
| `--platform PLATFORM` | 目标平台标签或预设，可多次指定 | 当前平台 |
| `--python-version VER` | 覆盖 Python 版本（如 `3.11`、`3.12`） | 当前 Python 版本 |
| `--exclude PKG` | 排除指定依赖，可多次指定 | 无 |
| `--include-extras EXTRA` | 包含 extras 依赖组，可多次指定 | 无 |
| `--prefer {wheel,source}` | 优先下载 wheel 还是源码包 | `wheel` |
| `--dry-run` | 仅预览将要下载的内容，不实际下载 | 关闭 |
| `--json` | 以 JSON 格式输出结果到标准输出 | 关闭 |

### 平台取值

单独的平台标签：

| 标签 | 操作系统 | 架构 |
|------|---------|------|
| `manylinux2014_x86_64` | Linux (glibc) | x86_64 |
| `manylinux2014_aarch64` | Linux (glibc) | ARM64 |
| `musllinux_1_2_x86_64` | Linux (musl) | x86_64 |
| `musllinux_1_2_aarch64` | Linux (musl) | ARM64 |
| `macosx_11_0_x86_64` | macOS | Intel |
| `macosx_11_0_arm64` | macOS | Apple Silicon |
| `win_amd64` | Windows | x86_64 |
| `win_arm64` | Windows | ARM64 |

预设：

| 预设 | 包含的平台 |
|------|-----------|
| `all` | 全部 8 个平台 |
| `linux` | 全部 4 个 Linux 变体 |
| `macos` | 两种 macOS 架构 |
| `windows` | 两种 Windows 架构 |

### 示例

```bash
# 为当前平台打包
depotpy pack /path/to/project

# 为指定平台打包
depotpy pack . --platform manylinux2014_x86_64 --platform macosx_11_0_arm64

# 为所有平台打包，包含 extras
depotpy pack . --platform all --include-extras dev

# 排除测试依赖打包
depotpy pack . --exclude pytest --exclude coverage

# 自定义输出目录和 Python 版本
depotpy pack . -o ./dist --python-version 3.12

# 优先下载源码包
depotpy pack . --prefer source

# 预览将要下载的内容（干跑模式）
depotpy pack . --platform all --dry-run

# 机器可读的 JSON 输出
depotpy pack . --json

# 调试模式，显示详细日志
depotpy -v pack .

# 静默模式，用于脚本
depotpy -q pack . --json
```

### 输出

在输出目录中创建名为 `{项目名}-{版本号}-offline.tar.gz` 的文件。

离线包内部结构：

```
{project_name}-{version}-offline/
  README.md          # 安装说明，包含精确的 pip 命令
  manifest.json      # 包清单（名称、版本、SHA-256 哈希）
  packages/          # 所有 .whl 和 .tar.gz 文件
```

---

## `depotpy inspect`

查看离线包的内容和元数据。

```bash
depotpy inspect <bundle_path> [选项]
```

### 参数

| 参数 | 说明 |
|------|------|
| `bundle_path` | `.tar.gz` 离线包文件路径 |

### 选项

| 选项 | 说明 | 默认值 |
|------|------|--------|
| `--json` | 以 JSON 格式输出结果到标准输出 | 关闭 |

### 示例

```bash
depotpy inspect myapp-1.0.0-offline.tar.gz

# 机器可读输出
depotpy inspect myapp-1.0.0-offline.tar.gz --json
```

### 输出

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

从离线包安装到当前 Python 环境。

```bash
depotpy install <bundle_path> [选项]
```

### 参数

| 参数 | 说明 |
|------|------|
| `bundle_path` | `.tar.gz` 离线包文件路径 |

### 选项

| 选项 | 说明 | 默认值 |
|------|------|--------|
| `--target DIR` | 安装到指定目录 | 当前环境 |
| `--on-conflict {keep,overwrite,error}` | 与已安装包冲突时的处理方式 | `keep` |
| `--json` | 以 JSON 格式输出结果到标准输出 | 关闭 |

`--on-conflict` 冲突策略：

| 策略 | 行为 |
|------|------|
| `keep` | 保留已安装的版本，跳过冲突的包 |
| `overwrite` | 强制重新安装离线包中的所有包 |
| `error` | 检测到版本冲突时报错退出 |

### 示例

```bash
# 安装到当前环境
depotpy install myapp-1.0.0-offline.tar.gz

# 安装到指定目录
depotpy install myapp-1.0.0-offline.tar.gz --target /opt/myapp/lib

# 强制重新安装所有包
depotpy install myapp-1.0.0-offline.tar.gz --on-conflict overwrite

# 存在版本冲突时报错
depotpy install myapp-1.0.0-offline.tar.gz --on-conflict error

# 机器可读输出
depotpy install myapp-1.0.0-offline.tar.gz --json
```

### 手动安装

目标机器上不需要安装 DepotPy，直接解压后用 pip 安装：

```bash
tar xzf myapp-1.0.0-offline.tar.gz
cd myapp-1.0.0-offline
pip install --no-index --find-links ./packages <包名列表>
```

离线包中的 `README.md` 包含了完整的安装命令。

---

## 退出码

| 退出码 | 含义 |
|--------|------|
| `0` | 成功 |
| `1` | 错误（文件不存在、项目无效、下载失败等） |

## 依赖管理器检测

DepotPy 自动检测项目使用的依赖管理工具：

| 优先级 | 工具 | 检测方式 | 使用的命令 |
|--------|------|---------|-----------|
| 1 | uv | `uv.lock` 或 `[tool.uv]` | `uv pip download` |
| 2 | poetry | `poetry.lock` 或 `[tool.poetry]` | 回退到 pip |
| 3 | pdm | `pdm.lock` 或 `[tool.pdm]` | 回退到 pip |
| 4 | pipenv | `Pipfile` 或 `Pipfile.lock` | 回退到 pip |
| 5 | pip | `requirements.txt`、`setup.py`、`setup.cfg` | `pip download` |

如果检测到的工具未安装在系统中，DepotPy 会自动回退到 pip 进行下载。
