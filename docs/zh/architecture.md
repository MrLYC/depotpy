# 架构设计

## 概述

PyDepot 采用流水线结构，将一个 Python 项目转换为自包含的离线安装包：

```
项目目录 → 检测 → 解析 → 下载 → 清单 → 打包 → .tar.gz
```

## 模块结构

```
src/pydepot/
├── __init__.py        # 公共 API 导出
├── cli.py             # argparse 入口，子命令分发
├── commands/
│   ├── pack.py        # pack 子命令处理
│   ├── inspect.py     # inspect 子命令处理 + BundleInspector
│   └── install.py     # install 子命令处理
├── detector.py        # 依赖管理器检测 + 项目元数据提取
├── models.py          # 数据模型（dataclasses + 枚举）
├── platforms.py       # 平台标签、预设和解析
├── resolver.py        # 通过 pip/uv 下载依赖
├── manifest.py        # manifest.json 序列化/反序列化
├── packer.py          # tar.gz 包创建 + PackBuilder
└── installer.py       # 离线包解压和 pip 安装
```

## 数据流

### 打包流程

```
1. CLI (cli.py)
   ↓ 解析参数 → PackOptions
2. PackBuilder (packer.py)
   ↓ 编排整个流程
3. detect_project (detector.py)
   ↓ 扫描项目文件 → ProjectInfo
4. resolve_platforms (platforms.py)
   ↓ 解析 --platform 参数 → list[PlatformTag]
5. download_packages (resolver.py)
   ↓ pip/uv 下载 → list[PackageFile]
6. Manifest (models.py)
   ↓ 组装元数据
7. _create_bundle_tarball (packer.py)
   ↓ tar.gz 包含 README + manifest + packages
8. 输出: {name}-{version}-offline.tar.gz
```

### 查看流程

```
1. CLI → BundleInspector
2. 打开 tar.gz，查找 manifest.json
3. 解析清单 → Manifest 对象
4. 打印摘要
```

### 安装流程

```
1. CLI → BundleInstaller
2. 解压 tar.gz 到临时目录
3. 查找 manifest.json → 获取包名列表
4. 执行: pip install --no-index --find-links ./packages <包名>
5. 清理临时目录
```

## 关键设计决策

### 零运行时依赖

PyDepot 仅使用 Python 标准库。外部工具（uv、poetry、pdm、pip）通过 `subprocess` 调用，在运行时检测，不作为包依赖声明。这使得 PyDepot 在受限环境中也能轻松安装。

### 依赖管理器检测

检测遵循严格的优先级顺序（uv > poetry > pdm > pipenv > pip）。每个管理器通过两个信号检测：

1. **锁文件存在** — `uv.lock`、`poetry.lock` 等
2. **pyproject.toml 中的工具段** — `[tool.uv]`、`[tool.poetry]` 等

如果检测到某个管理器但其 CLI 未安装（`shutil.which` 返回 None），PyDepot 会回退到下一个选项，最终到达 pip。

### 平台标签

平台标签遵循 [PEP 425](https://peps.python.org/pep-0425/) wheel 兼容标签方案。PyDepot 定义了 8 个常用平台标签，分为预设组（`all`、`linux`、`macos`、`windows`）。

未指定 `--platform` 时，仅使用当前平台。这是有意为之 — 跨平台包体积显著更大，大多数用户只需要自己平台的包。

### 下载策略

对每个平台，PyDepot 运行单独的 `pip download`（或 `uv pip download`）命令，带上 `--platform` 和 `--only-binary=:all:` 参数。这确保能正确获取平台特定的二进制 wheels。

文件下载到同一个扁平目录中。重复文件名（如同一个纯 Python wheel 被多个平台下载）由文件系统自然去重。

### 包格式

选择 `.tar.gz` 格式的原因：

- 通用支持 — 所有操作系统都能解压
- 压缩率 — 对于典型的 wheel 内容，比 zip 更小
- 流式处理 — 创建时无需 seek 操作
- 简单性 — 没有自定义格式，使用标准 tar

tar 内的顶层目录确保安全解压（不会散落文件）。

### 清单设计

`manifest.json` 有两个用途：

1. **机器可读**: 程序可以解析它来验证包内容
2. **完整性校验**: SHA-256 哈希值可用于验证每个包文件

清单在手动 pip 安装时不会被使用 — 它是一个可选的元数据层。

## 错误处理策略

错误分为三类：

| 异常类型 | 含义 | 示例 |
|---------|------|------|
| `FileNotFoundError` | 输入不存在 | 项目路径或离线包文件不存在 |
| `ValueError` | 输入无效 | 找不到项目配置、离线包中没有清单 |
| `RuntimeError` | 外部工具失败 | pip 下载或安装失败 |

每个 CLI 子命令捕获这些异常，向 stderr 输出友好的错误信息，返回退出码 1。

## 测试策略

测试文件与源码结构对应：

```
tests/
├── test_cli.py            # CLI 解析和分发
├── test_platforms.py       # 平台标签和解析
├── test_models.py          # 数据模型行为
├── test_detector.py        # 依赖管理器检测
├── test_resolver.py        # 下载命令构建和文件扫描
├── test_manifest.py        # 清单序列化往返测试
├── test_packer.py          # 包创建
├── test_inspect.py         # inspect 子命令
├── test_installer.py       # install 子命令
└── test_pack_command.py    # pack 子命令处理
```

外部工具调用（`pip download`、`pip install`）在 `subprocess.run` 层级进行 mock。文件系统操作使用 pytest 的 `tmp_path` fixture。
