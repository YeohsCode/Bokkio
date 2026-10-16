---
title: "Outlook Graph：PowerShell 登录与未读查询"
created: "2026-10-16"
updated: "2026-10-16"
type: "entity"
tags: ["runtime", "configuration", "office", "evidence"]
sources: ["docs/OUTLOOK-GRAPH.md", "docs/evidence/2026-10-16-outlook-powershell/README.md", "src/bokkio/outlook_graph.py", "src/bokkio/native/outlook_graph.ps1", "src/bokkio/runtime.py", "src/bokkio/local_runtime.py", "desktop/src/OutlookSettings.tsx"]
confidence: "high"
---

# Outlook Graph：PowerShell 登录与未读查询

Desktop 配置页使用官方 Microsoft.Graph.Authentication 默认注册应用，用户无需自建 Entra 应用。缺组件时准备 PowerShell 7 与认证模块；设备码只在当前 UI 显示，用户在微软页面登录确认。^[docs/OUTLOOK-GRAPH.md#L5]

## 身份与密码

CurrentUser SDK 缓存负责持久登录和令牌刷新；同机同系统用户通常首次登录后复用，撤销/退出或组织重新认证时再登录。Bokkio 不接收微软密码、不复制令牌；仅存账户、租户、范围并在请求时核对账户。Mac 与 Windows 各自登录，模型密钥仍由原系统加密存储负责。^[docs/OUTLOOK-GRAPH.md#L14]

## 工具与执行

- outlook.status：读取配置账户；configured 不代表当前访问有效。
- outlook.unread：按带时区的 [start,end) 统计 Inbox 当前未读邮件，跟随分页，只返回计数/范围/账户等摘要，不读取正文或发送邮件。
- Agent 工具调用进入 Runtime 操作回执；配置页管理与测试统计经 DesktopService 直接调用。Harness 编排 API 工具，Jev 不参与；日志不伪造局部决策。

^[src/bokkio/runtime.py#L412] ^[docs/OUTLOOK-GRAPH.md#L22]

纯 API/code 会话不枚举桌面应用；Graph 不需要 AX/UIA、屏幕采集或键鼠录制权限。原生录制/回放仍是独立能力，见 [[entities/runtime-workflow]]。^[src/bokkio/local_runtime.py#L19]

## 当前证据与接续

736 项 Python、9 项 Electron 测试通过；macOS/Windows 打包版 UI 各 10/10，使用真实 PowerShell 与离线 Graph cmdlet 夹具。正常安装版已显示真实微软设备码。用户当前不在电脑旁，要求先提交；真实邮箱和 SDK 跨重启登录复用尚未验证。^[docs/evidence/2026-10-16-outlook-powershell/README.md#L9]

回到电脑后在配置页重新连接，完成一次微软授权，再验证真实计数、重启后无交互查询以及退出/重连。参见 [[summaries/current-status]]、[[summaries/module-call-map]] 与 [[concepts/configuration-and-privacy]]。
