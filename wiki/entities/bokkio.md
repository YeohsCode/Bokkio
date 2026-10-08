---
title: "Bokkio：项目目标与边界"
created: "2026-10-08"
updated: "2026-10-08"
type: "entity"
tags: ["project", "architecture"]
sources: ["README.md", "docs/RESEARCH.md", "pyproject.toml"]
confidence: "high"
---

# Bokkio：项目目标与边界

Bokkio 用统一的原生桌面元素层支撑 Windows/macOS 操作、局部决策、任务规划和确定性重放。项目重点是 Computer Use，覆盖桌面和跨应用流程；浏览器只是可能的应用环境。^[docs/RESEARCH.md#L9]

## 当前技术边界

- 当前实现是 Python 包与 CLI，依赖 xa11y；Windows 使用 comtypes 补充 UIA，Mac 视觉 helper 使用 Swift。^[pyproject.toml#L5]
- Rust Runtime 和完整 CUP 协议适配属于设计方向，不能当作已经交付的实现。^[README.md#L1]
- 实现状态与应用覆盖是两个维度。373 项隔离测试不代表所有桌面任务可执行。^[docs/STATUS.md#L5]

## 阅读路线

先看 [[summaries/architecture-map]]，再按需要进入 [[entities/native-runtime]]、[[entities/desktop-agent]] 或 [[entities/workflow-engine]]。最新边界见 [[summaries/current-status]]。
