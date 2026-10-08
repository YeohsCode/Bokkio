---
title: "原生元素路径与视觉路径"
created: "2026-10-08"
updated: "2026-10-08"
type: "comparison"
tags: ["native", "vision", "architecture"]
sources: ["src/bokkio/xa11y_backend.py", "src/bokkio/macos_capture.py", "src/bokkio/visual.py", "src/bokkio/visual_input.py", "docs/P7-PLAN.md"]
confidence: "high"
---

# 原生元素路径与视觉路径

两条路径共享任务范围和验证要求，但身份、能力与执行支持不同；现有视觉能力尚未替代完整原生 Agent 链路。^[docs/P7-PLAN.md#L1]

| 维度 | 原生元素 | 当前视觉 |
|---|---|---|
| 观察 | OS role/name/value/state/tree | 限定窗口 PNG + OCR文字/框/置信度 |
| 目标身份 | structural ref + 原生补充身份 | 图像哈希、进程/窗口身份、区域 |
| 动作能力 | provider 声明与平台验证 | OCR 不声明控件语义或授权 |
| 执行 | Xa11yBackend.perform | Mac 显式 visual_input API，正向未验收 |
| Agent 集成 | 已有 Planner/Jev/Runtime loop | 自动降级未接入 |

实现入口对应 [[entities/native-runtime]]、[[entities/capture-and-ocr]] 与 [[entities/visual-input]]。^[src/bokkio/xa11y_backend.py#L123] ^[src/bokkio/visual.py#L40]

## 降级条件

无原生目标/能力时可以收集新视觉证据；原生派发结果未知时不能借另一条路径再点一次。候选歧义需要可区分的新范围或观察。^[docs/P7-PLAN.md#L37]

关联：[[concepts/action-verification]]、[[summaries/architecture-map]]。
