---
title: Bokkio LLM Wiki Index
created: 2026-10-08
updated: 2026-10-16
type: meta
tags: [meta, project]
sources: [docs/progress/STATUS.md, src/bokkio/runtime.py, pyproject.toml]
confidence: high
---

# Bokkio LLM Wiki

项目代码与证据的可维护知识库。Last updated: 2026-10-16 | Total compiled pages: 28

先读 [[SCHEMA]]；维护记录见 [[log]]。

快速入口：[[summaries/architecture-map]]、[[summaries/module-call-map]]、[[entities/runtime-core]]、[[concepts/runtime-contracts]]、[[summaries/current-status]]、[[summaries/pending-and-known-gaps]]。

当前主线为 **0.2.0 通用 Runtime**。当前架构／功能布局／调用关系／Core／Workflow／能力模块／状态页已刷新；旧 Planner/Jev/Workflow/Office/视觉专题保留各页 updated 日期的历史范围，最新验收及待办以当前状态和共享 progress 为准。

## 2026-10-16 增量

Desktop 0.3.0 新增 [[entities/outlook-graph]]，使用官方 Graph PowerShell 默认应用身份。当前改为通用 Graph GET，已移除专用未读按钮／工具；Harness 动态查询和汇总正文，真实账户与重启复用待用户登录；旧业务成绩保持各自日期范围。

## Entities

- [[entities/outlook-graph|Outlook Graph：连接与通用读取]] — SDK 登录缓存、统一账户入口与通用 Graph GET；真实账户验证待接续。

- [[entities/capability-modules|能力模块：发现、合同与Office文件实现]] — 默认关闭的模块目录、精确合同与文件证据，复用既有worker。
- [[entities/runtime-workflow|Runtime Workflow：Studio、录制与回放]] — 新版本库、精确启动身份、Core子动作与检查点；区别于历史直接backend引擎。

- [[entities/benchmark-adapters|外部 Benchmark 适配入口]] — WAA 逐步适配与 WindowsWorld Office pilot 是不同入口，历史适配专题，成绩不可换算为当前 Runtime 业务验收。
- [[entities/bokkio|Bokkio：项目目标与边界]] — 通用 Computer Use Runtime；调用方规划并独立验收业务，Core 执行并提供证据。
- [[entities/runtime-core|Computer Use Core：会话、执行与审计]] — 三种入口共用 Runtime.call，统一 Session、审批、四类通道、作业和审计。
- [[entities/capture-and-ocr|窗口采集与原生 OCR]] — 采集通过包内 API 和 `capture` CLI 独立于 AX/UIA 树提供图像；图像身份、时间和坐标必须跟随结果，不能只保存一张无上下文截图。
- [[entities/desktop-agent|DesktopAgent：阶段执行与恢复]] — `DesktopAgent.run()` 管理观察、阶段计划、Jev 决策、Runtime 动作、成功条件与持久化 trace。
- [[entities/native-runtime|原生 Runtime：xa11y 适配层]] — `Xa11yBackend` 是原生应用发现、树读取、元素查找与动作派发入口；Windows UIA 补充不替代整套树模型。
- [[entities/office-pilot|微软 Office 原题 pilot]] — 首批固定 WindowsWorld 三道 L1 原题，Mac 环境适配：Word 标题/正文格式、Excel D 列货币格式、PowerPoint 标题页。
- [[entities/planner-and-jev|Planner 与 Jev 的职责分工]] — Planner 规划阶段和成功条件；Jev 在当前观察的有限选项中选择动作与目标。
- [[entities/visual-input|有界视觉输入：代码与验收边界]] — Mac公共provider/Agent/CLI文字降级已实现；实机只读观察与Jev决策3/3，真实输入及视觉Workflow待验收/实现。
- [[entities/workflow-engine|Recorder 与 Workflow 引擎]] — Workflow 将成功语义执行固化为有依赖、前置条件、验证条件与版本哈希的可重放步骤；它不是无条件键鼠宏。

## Concepts

- [[concepts/runtime-contracts|Runtime 操作生命周期与证据合同]] — 观察、审批、幂等、派发、作业终态和独立验收的时序及身份/时效约束。

- [[concepts/action-verification|派发、确认与未知完成]] — 必须分别判断“尚未派发”“已调用但结果未知”“新观察确认完成”；异常不能自动当作零派发。
- [[concepts/configuration-and-privacy|配置、数据范围与隐私]] — Wiki 只记录配置接口和变量名称，凭据与 VM 认证文件不进入 Wiki 或 Git。
- [[concepts/element-identity|元素身份、Selector 与快照版本]] — ref 描述当前结构中的元素身份；它不等同于长期有效的 OS 对象指针。
- [[concepts/evidence-and-scoring|证据、评分与真实分母]] — 软件实现、隔离测试、原生动作、完整任务和官方评分是不同证据层，不能相互替代。
- [[concepts/permissions-and-sessions|权限与可用输入会话]] — 权限预检查通过与交互会话可用是不同条件。
- [[concepts/recovery-and-versioning|阶段恢复、需求修订与文件版本]] — 恢复需要核对当前事实，不能仅重放历史动作；需求修订需要区分旧结果和新目标。

## Comparisons

- [[comparisons/native-and-visual-paths|原生元素路径与视觉路径]] — 两条路径共享任务范围和验证要求，但身份、能力与执行支持不同；现有视觉能力尚未替代完整原生 Agent 链路。
- [[comparisons/windows-and-macos|Windows 与 Mac：能力和验收对照]] — 跨平台统一数据模型不意味着各平台已完成相同验收。

## Queries

- [[queries/extending-native-runtime|如何扩展原生动作而不破坏边界]] — 新增动作需要同时更新 capability、选择空间、实际派发和验证；单独加入 CLI action 名称不等于支持。
- [[queries/office-pilot-readiness|如何判断 Office 题库是否可以跑]] — 保留 2026-10-09 十轮证据；后续分轮成绩与当前产品状态见当前状态页。

## Summaries

- [[summaries/architecture-map|架构与代码导航]] — 当前系统设计、部署/线程/进程边界与旧扩展的位置。
- [[summaries/module-call-map|模块调用关系与完整代码地图]] — Core 模块图、全部工具路由、原生支持和旧扩展/评测文件地图。
- [[summaries/current-status|当前阶段与证据快照]] — 2026-10-13：647隔离回归／受控文件6/6；旧冻结业务主批 26/36、稳定性 17/27、GUI 0/18；客户及 Windows 当前 Runtime 待验收。
- [[summaries/pending-and-known-gaps|Pending 与已知集成缺口]] — 当前 MAC/EVAL/CLIENT/HARNESS/WIN/RELEASE 工作包及真实环境/客户验收缺口。

## Raw sources

初始42份来源及历次追加版本保留为不可变文本快照。本次追加 outlook-graph 版本，记录逐文件 commit/working-tree、正文 SHA-256；基线及记录见 raw/manifest.json。页面溯源指向仓库代码/文档，旧来源快照不覆盖。
