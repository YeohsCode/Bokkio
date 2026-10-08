---
title: "元素身份、Selector 与快照版本"
created: "2026-10-08"
updated: "2026-10-08"
type: "concept"
tags: ["selector", "runtime", "native"]
sources: ["src/bokkio/model.py", "src/bokkio/selector.py", "src/bokkio/xa11y_backend.py", "src/bokkio/workflow.py"]
confidence: "high"
---

# 元素身份、Selector 与快照版本

ref 描述当前结构中的元素身份；它不等同于长期有效的 OS 对象指针。重新启动、改名、兄弟关系或 provider 重建都可能使旧引用失效。^[src/bokkio/model.py#L43]

## 查询与派发

`choose()` 优先 ref，然后 role/name/parent；缺失与歧义返回结构化错误，没有选第一个候选的兜底。`tree_digest()` 将决策绑定到完整当前树；Runtime 派发前重建并校验。^[src/bokkio/selector.py#L14] ^[src/bokkio/xa11y_backend.py#L154]

## 重放上下文

Workflow selector 保留语义和命名上下文，允许受约束的恢复。Windows HWND/RuntimeId 补充原生身份；Mac 结构策略保留平台信息。恢复 ref 与改写动作是不同操作。^[src/bokkio/workflow.py#L47] ^[src/bokkio/xa11y_backend.py#L418]

关联：[[entities/native-runtime]]、[[entities/workflow-engine]]、[[concepts/action-verification]]。
