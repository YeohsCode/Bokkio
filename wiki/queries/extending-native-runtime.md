---
title: "如何扩展原生动作而不破坏边界"
created: "2026-10-08"
updated: "2026-10-08"
type: "query"
tags: ["runtime", "maintenance", "safety"]
sources: ["src/bokkio/xa11y_backend.py", "src/bokkio/decision.py", "src/bokkio/workflow.py", "tests/test_actions.py"]
confidence: "high"
---

# 如何扩展原生动作而不破坏边界

新增动作需要同时更新 capability、选择空间、实际派发和验证；单独加入 CLI action 名称不等于支持。^[src/bokkio/xa11y_backend.py#L13]

## 实施检查表

- 定义平台原始动作到统一动作的映射，保留平台信息。^[src/bokkio/xa11y_backend.py#L26]
- 在 perform 的派发前检查中维护作用域、enabled、声明能力及 snapshot 版本。^[src/bokkio/xa11y_backend.py#L123]
- `decision.options()` 必须仅提供真实且当前可用的选项，文字来自允许值。^[src/bokkio/decision.py#L38]
- Recorder/Workflow 参数、动作和验证协议也要相应校验；未知完成不要重放。^[src/bokkio/workflow.py#L123]
- 在自有 fixture 做新观察、动作后独立结果和错误状态测试；不要只断言函数被调用。^[tests/test_actions.py#L1]

## 先确认接口

修改公共接口时检查所有调用方。[[entities/office-pilot]] 的构造参数不匹配说明：测试覆盖 mock 边界不能替代真实 wiring 检查。

关联：[[entities/native-runtime]]、[[concepts/action-verification]]、[[entities/workflow-engine]]。
