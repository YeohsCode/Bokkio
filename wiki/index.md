---
title: Bokkio LLM Wiki Index
created: 2026-10-08
updated: 2026-10-09
type: meta
tags: [meta, project]
sources: [docs/STATUS.md]
confidence: high
---

# Bokkio LLM Wiki

项目代码与证据的可维护知识库。Last updated: 2026-10-09 | Total compiled pages: 22

先读 [[SCHEMA]]；维护记录见 [[log]]。

快速入口：[[summaries/architecture-map]]、[[summaries/current-status]]、[[summaries/pending-and-known-gaps]]。

## Entities

- [[entities/benchmark-adapters|外部 Benchmark 适配入口]] — WAA 逐步适配与 WindowsWorld Office pilot 是不同入口，不能把前者的 Explorer/Notepad 成绩换成微软 Office 成绩。
- [[entities/bokkio|Bokkio：项目目标与边界]] — Bokkio 用统一的原生桌面元素层支撑 Windows/macOS 操作、局部决策、任务规划和确定性重放。
- [[entities/capture-and-ocr|窗口采集与原生 OCR]] — 采集通过包内 API 和 `capture` CLI 独立于 AX/UIA 树提供图像；图像身份、时间和坐标必须跟随结果，不能只保存一张无上下文截图。
- [[entities/desktop-agent|DesktopAgent：阶段执行与恢复]] — `DesktopAgent.run()` 管理观察、阶段计划、Jev 决策、Runtime 动作、成功条件与持久化 trace。
- [[entities/native-runtime|原生 Runtime：xa11y 适配层]] — `Xa11yBackend` 是原生应用发现、树读取、元素查找与动作派发入口；Windows UIA 补充不替代整套树模型。
- [[entities/office-pilot|微软 Office 原题 pilot]] — 首批固定 WindowsWorld 三道 L1 原题，Mac 环境适配：Word 标题/正文格式、Excel D 列货币格式、PowerPoint 标题页。
- [[entities/planner-and-jev|Planner 与 Jev 的职责分工]] — Planner 规划阶段和成功条件；Jev 在当前观察的有限选项中选择动作与目标。
- [[entities/visual-input|有界视觉输入：代码与验收边界]] — Mac click/type/replace和限定Office字段输入已实现；较早OCR脚本探针通过，最新Agent路径尚未通过。
- [[entities/workflow-engine|Recorder 与 Workflow 引擎]] — Workflow 将成功语义执行固化为有依赖、前置条件、验证条件与版本哈希的可重放步骤；它不是无条件键鼠宏。

## Concepts

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
- [[queries/office-pilot-readiness|如何判断 Office 题库是否可以跑]] — 十轮三题已实际执行，各轮独立评分0/3；仍需修复Word确认、Excel守卫与PPT候选。

## Summaries

- [[summaries/architecture-map|架构与代码导航]] — 从入口到执行按模块职责阅读，比按提交时间浏览更容易定位改动。
- [[summaries/current-status|当前阶段与证据快照]] — 2026-10-09快照：P7部分验收、Office十轮实跑与411项主机回归。
- [[summaries/pending-and-known-gaps|Pending 与已知集成缺口]] — 按先修复可复现代码问题、再获取真实执行证据的顺序推进；环境恢复不是所有缺口的唯一条件。

## Raw sources

初始42份已提交来源及追加的恢复版本保存为不可变文本快照，正文哈希和基线提交见 raw/manifest.json。页面溯源仍指向仓库代码/文档。
