---
title: "Outlook Graph：连接与通用读取"
created: "2026-10-16"
updated: "2026-10-16"
type: "entity"
tags: ["runtime", "configuration", "office", "evidence"]
sources: ["docs/OUTLOOK-GRAPH.md", "docs/evidence/2026-10-16-graph-generic/README.md", "docs/evidence/2026-10-16-outlook-powershell/README.md", "src/bokkio/outlook_graph.py", "src/bokkio/native/outlook_graph.ps1", "src/bokkio/runtime.py", "src/bokkio/local_runtime.py", "desktop/src/OutlookSettings.tsx"]
confidence: "high"
---

# Outlook Graph：连接与通用读取

Desktop 配置页只管理官方 Graph PowerShell 连接：准备、登录、验证、取消、退出。没有业务查询按钮；使用默认注册应用，用户无需自建 Entra 应用。^[docs/OUTLOOK-GRAPH.md#L5]

## 身份与密码

CurrentUser SDK 缓存负责持久登录和令牌刷新；同机同系统用户通常首次登录后复用，撤销/退出或组织重新认证时再登录。Bokkio 不接收微软密码、不复制令牌；仅存账户、租户、范围并在请求时核对账户。Mac 与 Windows 各自登录，模型密钥仍由原系统加密存储负责。^[docs/OUTLOOK-GRAPH.md#L14]

## 工具与执行

- outlook.status：读取配置账户；configured 不代表当前访问有效。
- outlook.request：通用 Graph v1.0 GET，调用方传 path、OData query、max_pages，无时间／文件夹／未读状态业务默认值；返回属性与正文，保留 complete、next_link。
- Harness 根据自然语言问题确定查询和汇总，复用 code.run 计算；同一工具可完成计数、时间区间摘要或按发件人筛选。API 执行进入 Runtime 回执，不调用 Jev。
- Mail.Read 支持正文；旧 Mail.ReadBasic 连接需重新确认授权。正文优先 text，仍返回 HTML 时由调用方转换；大响应明确报错，不能把未取完的分页当作全量。

^[docs/OUTLOOK-GRAPH.md#L19] ^[src/bokkio/runtime.py#L412]

纯 API/code 会话不枚举桌面应用；Graph 不需要 AX/UIA、屏幕采集或键鼠录制权限。原生录制/回放仍是独立能力，见 [[entities/runtime-workflow]]。^[src/bokkio/local_runtime.py#L19]

## 当前证据与接续

原先专用未读查询及设置按钮已删除；旧报告保留其当时范围。本轮两端各完成3个真实模型对话任务（离线邮件），最终账户/界面生命周期各12/12；合并测试断言失败与后续HTTP402保留。验证记录见通用Graph专题。真实微软授权、用户邮箱和 SDK 跨重启复用仍待用户在电脑旁登录。^[docs/OUTLOOK-GRAPH.md#L60]

界面启动不再枚举原生应用；应用列表在控件拾取时加载。配置、凭据状态和对话初始化相互独立。参见 [[summaries/current-status]]、[[summaries/module-call-map]] 与 [[concepts/configuration-and-privacy]]。
