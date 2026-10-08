---
title: "阶段恢复、需求修订与文件版本"
created: "2026-10-08"
updated: "2026-10-08"
type: "concept"
tags: ["recovery", "workflow", "agent"]
sources: ["src/bokkio/agent.py", "src/bokkio/workflow_inputs.py", "src/bokkio/workflow.py", "src/bokkio/workflow_repair.py"]
confidence: "high"
---

# 阶段恢复、需求修订与文件版本

恢复需要核对当前事实，不能仅重放历史动作；需求修订需要区分旧结果和新目标。^[src/bokkio/agent.py#L194]

## Agent 状态

Trace 保存应用范围、动作预算、已完成完整子任务和需求修订版本。保留历史完成不意味着其旧 UI 状态必须再次写回。新 goal 必须通过明确 amendment 规则。^[src/bokkio/agent.py#L194]

## Workflow 与文件

参数声明、槽位和文件合约分别校验；输入/交付保留存在、长度、SHA-256，避免同名文件或被改动产物冒充完成。不同 PID 恢复需要重绑应用及窗口，不能延用旧 native handle。^[src/bokkio/workflow_inputs.py#L76] ^[src/bokkio/workflow.py#L338]

## 修复版本

模型候选修复保留 action/value/verification/scope，不做任意代码修复或直接执行；parent-linked 新版本单独验收。^[src/bokkio/workflow_repair.py#L20] ^[src/bokkio/workflow.py#L487]

关联：[[entities/workflow-engine]]、[[concepts/element-identity]]、[[concepts/action-verification]]。
