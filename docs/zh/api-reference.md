# Python API 参考

DepotPy 提供三个主要类用于编程调用：

```python
from depotpy import PackBuilder, BundleInspector, BundleInstaller
```

## PackBuilder

从 Python 项目构建离线安装包。

### 构造函数

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

### 方法

#### `build() -> tuple[Path, Manifest]`

执行完整的构建流程：检测项目、解析依赖、下载 wheels、生成清单、创建 tar.gz 包。

**返回**: 元组 (创建的 `.tar.gz` 文件路径, Manifest 对象)。

**异常**:
- `FileNotFoundError` — 项目路径不存在
- `ValueError` — 无法检测到项目配置
- `RuntimeError` — 依赖下载失败

```python
bundle_path, manifest = builder.build()
print(f"离线包已创建: {bundle_path}")
print(f"总包数: {manifest.package_count}")
```

---

## BundleInspector

查看离线包的内容。

### 构造函数

```python
from depotpy.commands.inspect import BundleInspector
from pathlib import Path

inspector = BundleInspector(Path("myapp-1.0.0-offline.tar.gz"))
```

### 方法

#### `get_manifest() -> dict`

提取并返回离线包中的原始清单数据。

**返回**: 包含清单内容的字典。

**异常**:
- `FileNotFoundError` — 离线包文件不存在
- `ValueError` — 离线包中没有 manifest.json

```python
data = inspector.get_manifest()
print(data["project_name"])    # "myapp"
print(data["packages"])        # 包信息列表
```

#### `print_summary() -> None`

向标准错误输出打印可读的摘要信息。

```python
inspector.print_summary()
```

---

## BundleInstaller

从离线包安装。

### 构造函数

```python
from depotpy.installer import BundleInstaller
from pathlib import Path

installer = BundleInstaller(Path("myapp-1.0.0-offline.tar.gz"))
```

### 方法

#### `install(target: str | None = None, on_conflict: ConflictPolicy = ConflictPolicy.KEEP) -> None`

解压离线包并通过 pip 安装。

**参数**:
- `target` — 可选的安装目标目录（pip 的 `--target` 参数）
- `on_conflict` — 与已安装包冲突时的处理方式（见 `ConflictPolicy`）

**异常**:
- `FileNotFoundError` — 离线包文件不存在
- `ValueError` — 离线包中没有清单文件
- `RuntimeError` — pip install 执行失败，或 `ConflictPolicy.ERROR` 策略下检测到冲突

```python
from depotpy.models import ConflictPolicy

# 安装到当前环境
installer.install()

# 安装到指定目录
installer.install(target="/opt/myapp/lib")

# 强制重新安装所有包
installer.install(on_conflict=ConflictPolicy.OVERWRITE)

# 存在版本冲突时报错退出
installer.install(on_conflict=ConflictPolicy.ERROR)
```

---

## 数据模型

### PackOptions

打包命令的选项。

```python
from depotpy.models import PackOptions, PackagePreference
from pathlib import Path

options = PackOptions(
    project_path=Path("."),        # 必填：项目根目录
    output_dir=Path("./dist"),     # 必填：输出目录
    platforms=[],                  # 可选：平台标签或预设
    python_version=None,           # 可选：覆盖 Python 版本
    exclude=[],                    # 可选：要排除的依赖
    include_extras=[],             # 可选：要包含的 extras
    prefer=PackagePreference.WHEEL,  # 可选：wheel 或源码包偏好
)
```

### ProjectInfo

检测到的项目元数据，由 `detect_project()` 返回。

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

表示一个已下载的包文件。

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

manifest.json 的内容。

```python
from depotpy.models import Manifest

manifest = Manifest(
    project_name="myapp",
    project_version="1.0.0",
    python_version="3.11",
    platforms=["manylinux2014_x86_64"],
    packages=[...],               # PackageFile 列表
)

manifest.package_count    # 包数量
manifest.total_size       # 总大小（字节）
```

### DependencyManager

支持的依赖管理器枚举。

```python
from depotpy.models import DependencyManager

DependencyManager.UV        # "uv"
DependencyManager.POETRY    # "poetry"
DependencyManager.PDM       # "pdm"
DependencyManager.PIPENV    # "pipenv"
DependencyManager.PIP       # "pip"
```

### PackagePreference

包格式偏好枚举。

```python
from depotpy.models import PackagePreference

PackagePreference.WHEEL     # "wheel" — 优先预编译 wheel（默认）
PackagePreference.SOURCE    # "source" — 优先源码分发包
```

### ConflictPolicy

已安装包冲突处理策略枚举。

```python
from depotpy.models import ConflictPolicy

ConflictPolicy.KEEP         # "keep" — 保留已安装版本，跳过冲突（默认）
ConflictPolicy.OVERWRITE    # "overwrite" — 强制从离线包重新安装
ConflictPolicy.ERROR        # "error" — 检测到冲突时中止
```

---

## 工具函数

### 平台解析

```python
from depotpy.platforms import resolve_platforms, get_current_platform

# 获取当前平台
current = get_current_platform()
print(current.tag)    # 如 "manylinux2014_x86_64"

# 解析平台参数
platforms = resolve_platforms(["linux", "macosx_11_0_arm64"])
# 返回: [MANYLINUX_X86_64, MANYLINUX_AARCH64, MUSLLINUX_X86_64, MUSLLINUX_AARCH64, MACOSX_ARM64]
```

### 清单 I/O

```python
from depotpy.manifest import write_manifest, read_manifest

# 写入
write_manifest(manifest, Path("manifest.json"))

# 读取
manifest = read_manifest(Path("manifest.json"))
```

### 依赖检测

```python
from depotpy.detector import detect_project
from pathlib import Path

info = detect_project(Path("/path/to/project"))
```
