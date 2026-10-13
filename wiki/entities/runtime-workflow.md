---
title: "Runtime Workflow：Studio、录制与回放"
created: "2026-10-13"
updated: "2026-10-13"
type: "entity"
tags: ["workflow", "runtime", "recovery", "safety", "evidence"]
sources: ["src/bokkio/workflow_studio.py", "src/bokkio/app_launch.py", "src/bokkio/native/macos_record.swift", "src/bokkio/runtime_workflow.py", "docs/WORKFLOW-STUDIO.md", "src/bokkio/manual_recording.py", "src/bokkio/runtime.py", "docs/progress/STATUS.md"]
confidence: "high"
---

# Runtime Workflow：Studio、录制与回放

新Workflow入口由本机Studio、被动录制、JSON版本库和RuntimeWorkflowRunner组成。它通过SDK进入当前Core，与历史workflow.py的直接backend重放分开。^[src/bokkio/runtime_workflow.py#L1] ^[docs/WORKFLOW-STUDIO.md#L1]

## 功能与持久化

Studio提供新建、录制、查看、编辑、调整步骤、版本历史、归档、回放与运行记录。WorkflowLibrary保存bokkio.runtime-workflow.v1、应用安装身份、语义选择器、参数、等待／完成检查和内容SHA。编辑产生新版本，运行冻结保存版本；不保存旧PID或坐标作为长期身份。^[src/bokkio/runtime_workflow.py#L10] ^[src/bokkio/runtime_workflow.py#L73]

manual_recording与macos_record.swift被动观察所选应用的事件／文本，捕获器不再次派发动作。未识别手势进入待审阅；Windows监听未完成实机验收。^[src/bokkio/manual_recording.py#L9] ^[docs/WORKFLOW-STUDIO.md#L17]

## 授权、启动与恢复

workflow.list/get/run/status/resume/cancel经过Runtime；workflows允许列表限制访问。启动应用用desktop.launch精确launch_apps身份，随后绑定新PID；Runner的子动作仍各自使用原有授权、审批与审计。^[src/bokkio/runtime.py#L405] ^[src/bokkio/runtime_workflow.py#L161]

每个动作先保存operation ID，再调用Core；中断恢复查回相同回执。明确零派发的过时观察可有界重新观察并新审批；未知完成停止，已派发动作不重复。^[src/bokkio/runtime_workflow.py#L133] ^[src/bokkio/runtime_workflow.py#L174]

后台桌面headless仅支持不抢前台／不派发鼠标键盘的原生传输，仍需未锁定交互桌面／WindowServer。网页支持Chromium有头／无头，代码模式由脚本依赖决定。^[docs/WORKFLOW-STUDIO.md#L73]

## 证据与限制

Workflow初轮613隔离回归、独立前台／鼠标见证5/5；新增能力模块后的回归647并不产生新的Workflow自主业务分数。完整业务复测保持暂停，真实用户端到端、客户软件、Windows监听与额外物理环境仍待验收。^[docs/progress/STATUS.md#L7] ^[docs/progress/STATUS.md#L9]

关联：[[entities/workflow-engine]]、[[entities/runtime-core]]、[[entities/capability-modules]]、[[summaries/module-call-map]]、[[summaries/current-status]]。
