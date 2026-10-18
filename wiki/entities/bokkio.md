---
title: "Bokkio：项目目标与边界"
created: "2026-10-08"
updated: "2026-10-18"
type: "entity"
tags: ["project", "architecture", "runtime"]
sources: ["README.md", "pyproject.toml", "src/bokkio/runtime.py", "docs/progress/STATUS.md"]
confidence: "high"
---

# Bokkio：项目目标与边界

Bokkio 当前是面向 Windows/macOS 的通用 Computer Use Runtime，供 Harness、Agent IDE、Agent 调用。调用方理解任务、选择原生/像素/代码/Browser 并核验业务结果；Core 提供获准资源上的执行和证据。Planner/Jev与历史workflow.py是保留的旧扩展；新Runtime Workflow和可选能力模块通过当前Core复用执行与证据。^[README.md#L29]

## 当前技术边界（2026-10-13）

- Python 包 0.2.0，Core ≥3.9、MCP ≥3.10；xa11y 0.15.x，Windows comtypes 补充 UIA，Mac Swift helper 支持采集/输入/激活。^[pyproject.toml#L7]
- MCP stdio、CLI JSON、Python SDK 共用 Runtime.call；Session、资源授权、独立审批、持久作业、审计和 artifact 构成新的会话授权、执行与结果记录流程。^[src/bokkio/runtime.py#L61]
- Rust 与完整 CUP 适配是后续方向；当前不提供逐文件 OS 沙箱、远程 fleet、多租户 SSO 或集中防篡改日志。^[README.md#L29] ^[docs/progress/STATUS.md#L56]
- 当前开发证据和完整产品/客户验收是不同维度；647 项隔离回归不表示所有桌面任务成功，Windows 当前 Runtime 尚未完成独立实机验收。^[docs/progress/STATUS.md#L13]

## 新增复用能力

默认关闭的office.xlsx文件模块提供语义能力与完整接口定义；Studio提供新版Workflow管理／录制／回放。两者不接管Harness目标规划。 ^[docs/progress/STATUS.md#L13]

## 阅读路线

设计看 [[summaries/architecture-map]]；具体调用看 [[summaries/module-call-map]]；统一边界看 [[entities/runtime-core]] 和 [[concepts/runtime-contracts]]；底层看 [[entities/native-runtime]]。当前事实见 [[summaries/current-status]]；旧可选能力见 [[entities/desktop-agent]]、[[entities/workflow-engine]]、[[entities/runtime-workflow]]、[[entities/capability-modules]]。
