---
title: "Planner 与 Jev 的职责分工"
created: "2026-10-08"
updated: "2026-10-08"
type: "entity"
tags: ["planner", "jev", "agent"]
sources: ["src/bokkio/planner.py", "src/bokkio/jev.py", "src/bokkio/decision.py"]
confidence: "high"
---

# Planner 与 Jev 的职责分工

Planner 规划阶段和成功条件；Jev 在当前观察的有限选项中选择动作与目标。二者都不能直接绕过 Runtime 派发动作。^[src/bokkio/planner.py#L18] ^[src/bokkio/decision.py#L270]

## Planner

`OpenRouterPlanner.plan()` 接收目标、当前观察及进度，返回经 `validate_plan()` 校验的子任务、应用/窗口范围、允许文字、风险和可观察成功条件。`continue_after_steps` 用于阶段延续。模型、配置与推理强度可覆盖。^[src/bokkio/planner.py#L148]

## Jev

`JevProvider.ask()` 使用 OpenRouter Decisions 或 TypeSafe endpoint。`options()` 只构造观察中的动作/目标与调用方允许的文字；返回分布、置信度和目标均需验证。大树上下文收窄保留同名候选。^[src/bokkio/jev.py#L25] ^[src/bokkio/decision.py#L38]

当前 OCR 候选没有自动接入这条规划/决策链路。不要把独立视觉 CLI 等同于 Jev 已能操作视觉目标。^[docs/STATUS.md#L5]

关联：[[entities/desktop-agent]]、[[entities/capture-and-ocr]]、[[concepts/configuration-and-privacy]]。
