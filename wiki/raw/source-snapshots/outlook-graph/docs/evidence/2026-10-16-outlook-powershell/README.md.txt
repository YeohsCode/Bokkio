---
source_path: docs/evidence/2026-10-16-outlook-powershell/README.md
source_version: working-tree-based-on-404b413b4e980acdd9f1975e8630c877f2278d05
ingested: 2026-10-16
sha256: 6546afc906d3397cacb1017a455e1359d6ea2725f5e8efe4898f995b0d7979c8
---

# Outlook Graph / PowerShell：2026-10-16

## 实现

Desktop 配置页增加 Microsoft / Outlook 账户卡片，提供准备组件、连接、设备码、取消、验证、退出和本周未读统计。固定 `.ps1` 使用官方 Graph PowerShell 默认应用身份与 `CurrentUser` 缓存；Bokkio 不持有微软密码，不复制访问/刷新令牌。portable PowerShell 从微软官方发布下载并核对 SHA256，认证模块来自 PowerShell Gallery。

API 查询通过只读 `outlook.unread` 接入共享 Runtime；纯 API/code 会话不再先枚举桌面应用。真实原生操作仍按原权限执行。Graph 查询由 Harness 选择工具和 Runtime/PowerShell 执行，不虚构 Jev 参与。

## 验证结果

| 检查 | 结果 | 范围 |
|---|---:|---|
| Python 完整回归 | 736 通过 | 包含 7 项 Graph 进程/会话测试与 3 项真实 PowerShell 脚本夹具测试 |
| Electron 单元测试 | 9 通过 | 已有启动、凭据和录制编辑回归 |
| TypeScript / Vite | 通过 | 两个平台打包 |
| macOS 打包版实际 UI | 10/10 | 真实 Electron + PowerShell；自有离线 Graph cmdlet 夹具 |
| Windows ARM64 打包版实际 UI | 10/10 | 相同夹具；不是实际 Microsoft 账户登录 |
| macOS 签名与来源对照 | 通过 | 安装版正常启动后，主应用和原生执行文件严格校验 |
| Windows 来源对照 | 通过 | packaged Python、PowerShell 脚本与前端来源一致 |
| 真实 Microsoft 登录前半程 | 已观察 | 正常启动的 macOS 安装版获得真实设备码，配置页显示，微软登录网页可打开 |
| 真实邮箱与登录持久性 | 待用户登录 | 用户明确表示当前不在电脑旁，先更新文档并提交 |

UI 夹具覆盖：设置页连接、实际 `.ps1` 两页计数、应用重启后重新检查、只保存非密钥账户字段、退出删除连接记录、设备码显示、取消终止等待以及取消后继续导航。夹具计数不作为用户邮箱数量，重启检查不作为真实 SDK 令牌持久性结论。

## 实测修正

- SDK 2.41.2 的真实设备码地址为 `login.microsoft.com/device`，与旧 `microsoft.com/devicelogin` 提示不同；兼容两种官方提示，以及警告流、直接控制台输出和无换行输出。后台检查遇到设备码便停止并要求显式登录。
- Windows 的 Python HTTPS 下载出现证书链/SSL 错误。组件下载优先使用系统 curl 的 HTTPS 校验，并保留发布资产 SHA256 核验；没有关闭证书验证。
- Windows UI 夹具首次未找到测试模块，根因是 Node 环境包含大小写重复的 `PSModulePath`；修正测试环境后，两端相同 UX 检查通过。

## 证据

- [macOS UI 结果](macos-ui.json) / [截图](macos-outlook.png)
- [Windows UI 结果](windows-ui.json) / [截图](windows-outlook.png)
- [macOS 安装版审计](macos-package-audit.json)
- [Windows 打包审计](windows-package-audit.json)
- [验证汇总](report.json)

截图均来自自有离线账户夹具；不提交真实账户、设备码、邮件、令牌、缓存或主机私有配置。
