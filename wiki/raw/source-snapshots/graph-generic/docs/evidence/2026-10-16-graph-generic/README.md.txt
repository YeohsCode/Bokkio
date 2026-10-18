---
source_path: docs/evidence/2026-10-16-graph-generic/README.md
source_version: working-tree-based-on-90caa22fa8283ed60401fd0a059821424a113bbc
ingested: 2026-10-16
sha256: 44288c18bac92bc0be409397ace6d36b9d63f7a27cee070d8fb028352493dfc7
text_revised: 2026-10-18
revision_reason: user-requested plain-language terminology
original_body_sha256: 76b22ff4dc098df37620417743a5a290f30f12491ecd650d690cddb31e8560be
---

# 移除业务写死，改为通用 Graph 读取（2026-10-16）

## 修改结果

删除配置页“本周未读”按钮、outlook.unread 工具、Desktop 专用查询路由、Python unread 方法和 PowerShell 固定过滤/计数分支。配置页只管理连接；outlook.request 接受资源路径、查询参数和页数，返回结构化属性、正文、完整性和续页。Harness 负责理解需求与汇总，可复用 code.run，不为新问题增加工具或发布。

授权改为 Mail.Read；只读 GET 执行不要求桌面辅助功能。旧 Basic 连接需重新确认正文授权。修复了读取长 JSON 时旧64 KiB缓冲清空的问题；超大响应明确报错，查询参数按 RFC 3986 编码，不丢数据后返回成功。背景检查遇到设备码仍停止等待，由用户显式连接。

真实 Windows UX 暴露了启动时枚举原生应用的 COM 错误：它会使凭据 UI 一直处于加载状态。现将配置、凭据及界面初始化分开，应用列表延迟至打开拾取器；Windows 枚举线程显式初始化/释放 COM。两端实际打开拾取器并取得应用选项。

## 验证范围与结果

| 检查 | 结果 | 实际范围 |
|---|---:|---|
| Python 完整回归 | 750 通过 | 含通用 Graph 接口与结果检查、真正的子进程与 PowerShell 夹具 |
| 最终 URI 编码修订后定向回归 | 24 通过 | 编码、续页、正文、大响应、服务错误与连接流程 |
| Electron 单元 | 9 通过 | 凭据并发、启动与已有录制编辑检查 |
| 两端打包版账户/界面生命周期 | 各 12/12 | 无业务按钮、连接、Mail.Read说明、拾取器、重启、退出、设备码、取消、导航 |
| Windows 最终通用读取补充 | 5 通过 | 真实PowerShell；正文、续页、合并、文件夹、退出 |
| macOS 真实模型对话 | 3 个任务完成 | 真实Harness/模型；离线邮件、实际脚本；同一工具动态查询 |
| Windows ARM64 真实模型对话 | 3 个任务完成 | 同上；模型通过仅面向虚拟机的临时转发访问，真实Provider Key未放入Windows |
| 来源与签名 | 通过 | 两端来源对照；macOS主包及原生执行文件严格签名 |
| 真实微软邮箱和缓存复用 | 待用户登录 | 没有将离线夹具称为真实邮箱 |

三种真实界面任务为“最近24小时未读”“最近12小时正文汇总，包含已读和未读”“最近24小时按发件人查询”。邮件夹具每页最多一封，验证模型实际使用参数化请求并跟随续页；正文中的22:00、林舟、730元都被读出。Runtime操作表确认无原生界面选择调用，启用Jev时也不伪造Jev参与。

模型任务完成后，合并套件因测试等待原生select的option“可见”而失败，实际选项已加载；改为等待挂载，最终生命周期各12项通过。保留模型运行中的失败记录，不将整个合并套件写为18/18。后续模型复跑遇到HTTP402，停止继续消耗调用。

一份Windows答案把UTC开始时间误标为本地时间；实际Graph过滤与邮件选择是12小时。这里证明动态请求、正文读取和分页，不把模型自然语言答案视为已完成全面业务验收。

## 文件

- [汇总](report.json)
- [macOS 模型运行](macos-model-run.json) / [Windows 模型运行](windows-model-run.json)
- [macOS 最终生命周期](macos-lifecycle.json) / [Windows 最终生命周期](windows-lifecycle.json)
- [Windows 读取补充](windows-transport.json)
- [macOS 账户UI](macos-settings.png) / [Windows 账户UI](windows-settings.png)
- [macOS 对话日志UI](macos-chat.png) / [Windows 对话日志UI](windows-chat.png)
- [macOS 摘要原文](macos-summary.txt) / [Windows 摘要原文](windows-summary.txt)
- [macOS 包审计](macos-package-audit.json) / [Windows 包审计](windows-package-audit.json)

截图和正文来自自有离线数据；没有微软用户账户、真实邮件、设备码、令牌或SDK缓存。旧版固定计数实现及其历史10/10报告见相邻outlook-powershell专题；当前接口以[连接指南](../../OUTLOOK-GRAPH.md)为准。
