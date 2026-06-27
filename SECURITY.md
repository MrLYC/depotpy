# Security Policy / 安全策略

## Supported Versions / 支持的版本

| Version | Supported |
|---------|-----------|
| 1.0.x   | Yes       |
| < 1.0   | No        |

## Reporting a Vulnerability / 报告漏洞

If you discover a security vulnerability, please report it responsibly:
如果您发现安全漏洞，请通过以下方式负责任地报告：

1. **Do NOT** open a public GitHub issue.
   **请勿**直接创建公开的 GitHub issue。

2. Email the maintainer at **imyikong@gmail.com** with:
   请发送邮件至 **imyikong@gmail.com**，包含以下信息：

   - Description of the vulnerability / 漏洞描述
   - Steps to reproduce / 复现步骤
   - Potential impact / 潜在影响
   - Suggested fix (if any) / 建议的修复方案（如有）

3. You will receive a response within **72 hours**.
   您将在 **72 小时**内收到回复。

4. A fix will be released as a patch version as soon as possible.
   修复将尽快作为补丁版本发布。

## Security Considerations / 安全考虑

DepotPy handles tar archives and executes subprocess commands. The following mitigations are in place:
DepotPy 处理 tar 归档文件并执行子进程命令。以下安全措施已实施：

- **Tarball extraction** uses `filter="data"` to prevent symlink and device file attacks.
  **Tar 提取**使用 `filter="data"` 防止符号链接和设备文件攻击。
- **Archive filenames** are sanitized with `Path.name` to prevent path traversal.
  **归档文件名**使用 `Path.name` 清理以防止路径穿越。
- **Subprocess calls** use list arguments (not `shell=True`) to prevent shell injection.
  **子进程调用**使用列表参数（而非 `shell=True`）以防止 shell 注入。
- **No runtime dependencies** — only Python standard library, minimizing supply chain risk.
  **无运行时依赖** — 仅使用 Python 标准库，最小化供应链风险。
- **SHA-256 hashes** in manifest.json for package integrity verification.
  **SHA-256 哈希**保存在 manifest.json 中，用于包完整性校验。
