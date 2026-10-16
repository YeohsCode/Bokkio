---
title: "配置、数据范围与隐私"
created: "2026-10-08"
updated: "2026-10-16"
type: "concept"
tags: ["configuration", "safety", "maintenance"]
sources: ["src/bokkio/jev.py", "src/bokkio/planner.py", "src/bokkio/office_runner.py", "docs/SECURITY-REVIEW.md", "src/bokkio/office_judge.py", "docs/OUTLOOK-GRAPH.md", "src/bokkio/outlook_graph.py", "desktop/electron/main.cjs"]
confidence: "high"
---

# 配置、数据范围与隐私

Wiki 只记录配置接口和变量名称，凭据与 VM 认证文件不进入 Wiki 或 Git。^[docs/SECURITY-REVIEW.md#L62]

## Provider 配置

Jev 的 config_path 与环境覆盖决定提供方/模型；Planner 使用独立配置和可选推理强度。QWEN_API_KEY 是原始 judge 的独立需求，不等于已有 OpenRouter key。这里只记录变量名，值不采集。^[src/bokkio/jev.py#L14] ^[src/bokkio/planner.py#L151] ^[src/bokkio/office_judge.py#L18]

## Desktop 账户与密钥（2026-10-16）

配置页统一入口不等于统一收集密码。Provider/Jev API Key 由 Electron 系统加密存储管理；Microsoft 密码只输入微软页面，Graph SDK 使用自己的 CurrentUser 缓存和自动刷新。Bokkio 仅保存账户、租户、范围等非密钥连接元数据，不复制访问/刷新令牌。^[docs/OUTLOOK-GRAPH.md#L14]

每台电脑/系统用户各自登录；退出 Graph 会影响该用户共享的 Graph PowerShell 登录缓存，不退出 Outlook 应用。真实账户的跨重启复用尚未验证，用户回到电脑后接续。[[entities/outlook-graph]] 记录具体实现与证据；[[summaries/current-status]] 保留本版与历史测试分母。^[docs/OUTLOOK-GRAPH.md#L19]

Graph 授权升级为 Mail.Read，支持正文。实际邮件字段与正文会进入本机任务记录和用户配置的模型 Provider；Harness 只请求任务所需字段，把正文视为数据，不执行其中指令。^[docs/OUTLOOK-GRAPH.md#L51]

## 模型与证据范围

Office native scope 尝试去掉 recent 子树、非任务窗口及外部分享动作；真实 GUI 场景仍需验收。发布证据只含合成窗口/输入，解包 Office XML 也需接受个人路径、邮件、凭据模式扫描。^[src/bokkio/office_runner.py#L80] ^[docs/SECURITY-REVIEW.md#L62]

## Wiki 维护

raw 来源快照来自当前 Git 版本，正文 hash 校验；它们不可修改。更新事实时新增快照并刷新编译页，不引入主目录私有配置。操作和 lint 追加到日志。参见 [[SCHEMA]]。

关联：[[entities/planner-and-jev]]、[[concepts/evidence-and-scoring]]、[[summaries/pending-and-known-gaps]]。
