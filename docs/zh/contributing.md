# 贡献指南

## 开发环境搭建

```bash
# 克隆仓库
git clone https://github.com/MrLYC/depotpy.git
cd depotpy

# 以开发模式安装，包含开发依赖
pip install -e ".[dev]"

# 验证
depotpy --version
pytest tests/ -v
```

## 项目结构

```
depotpy/
├── src/depotpy/         # 源码（src layout）
│   ├── cli.py           # CLI 入口
│   ├── commands/        # 子命令处理
│   ├── detector.py      # 依赖管理器检测
│   ├── resolver.py      # 包下载
│   ├── manifest.py      # 清单 I/O
│   ├── packer.py        # 包创建
│   ├── installer.py     # 包安装
│   ├── models.py        # 数据模型
│   └── platforms.py     # 平台定义
├── tests/               # 测试套件
├── docs/                # 文档
│   ├── en/              # 英文
│   └── zh/              # 中文
├── pyproject.toml       # 项目元数据和构建配置
└── README.md            # 项目概览
```

## 运行测试

```bash
# 运行所有测试
pytest tests/ -v

# 带覆盖率运行
pytest tests/ --cov=depotpy --cov-report=term-missing

# 运行特定测试文件
pytest tests/test_detector.py -v

# 运行特定测试
pytest tests/test_detector.py::TestDetectManager::test_uv_by_lockfile -v
```

## 代码风格

- 欢迎使用 Python 3.11+ 特性（类型标注、`match`、`tomllib` 等）
- 使用 `from __future__ import annotations` 进行延迟求值
- 优先使用标准库，尽量减少外部依赖
- 使用 `dataclasses` 定义数据模型
- 外部工具调用通过 `subprocess.run`

## 添加新的依赖管理器

1. 在 `models.py` 的 `DependencyManager` 枚举中添加新成员
2. 在 `detector.py` 中添加检测逻辑：
   - 检查锁文件或工具段
   - 通过 `shutil.which` 验证工具是否已安装
3. 如果该工具有自己的下载命令，在 `resolver.py` 中添加下载函数
4. 更新 `download_packages()` 以路由到新函数
5. 添加检测和下载的测试
6. 更新文档

## 添加新的平台

1. 在 `platforms.py` 中添加 `PlatformTag` 常量
2. 将其添加到相应的预设组（`PLATFORM_PRESETS`）
3. 添加测试
4. 更新文档

## 编写测试

- 文件系统测试使用 `tmp_path`（pytest fixture）
- 外部工具调用 mock `subprocess.run`
- 工具检测测试 mock `shutil.which`
- 每个模块有对应的测试文件（`test_{module}.py`）
- 用类组织相关测试

## 提交信息

使用清晰、描述性的提交信息：

```
Add support for conda dependency manager

Detect conda environments via environment.yml and use conda to resolve
dependencies. Falls back to pip when conda is not available.
```

## Pull Request

- PR 应专注于单个变更
- 新功能需包含测试
- 如果用户界面发生变化，需更新文档
- 确保所有测试通过，覆盖率不降低
