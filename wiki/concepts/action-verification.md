---
title: "派发、确认与未知完成"
created: "2026-10-08"
updated: "2026-10-08"
type: "concept"
tags: ["safety", "runtime", "evidence"]
sources: ["src/bokkio/xa11y_backend.py", "src/bokkio/workflow.py", "src/bokkio/visual_input.py", "src/bokkio/agent.py"]
confidence: "high"
---

# 派发、确认与未知完成

必须分别判断“尚未派发”“已调用但结果未知”“新观察确认完成”；异常不能自动当作零派发。^[src/bokkio/xa11y_backend.py#L123]

## 三层验证

- Native Runtime 检查范围、enabled、声明能力及派发前树，动作后读回。^[src/bokkio/xa11y_backend.py#L154]
- Workflow 在检查点保留 dispatching/verifying 阶段；回执未知时拒绝重复重放。^[src/bokkio/workflow.py#L338]
- Visual input 将无有效回执/后置证据归为未知，原函数没有自动重试。^[src/bokkio/visual_input.py#L39]

## 不能泛化的保证

DesktopAgent 有有界重规划错误分支。将视觉执行器接入 Agent 时，需要把已派发未知的错误传播成停止条件，不能只沿用一般 BokkioError 重规划逻辑。该全链路属性属于未完成的 P7 集成验收。^[src/bokkio/agent.py#L489] ^[docs/PENDING.md#L5]

关联：[[entities/desktop-agent]]、[[entities/visual-input]]、[[concepts/recovery-and-versioning]]。
