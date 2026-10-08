---
title: "Recorder 与 Workflow 引擎"
created: "2026-10-08"
updated: "2026-10-08"
type: "entity"
tags: ["workflow", "recovery", "runtime"]
sources: ["src/bokkio/workflow.py", "src/bokkio/workflow_inputs.py", "src/bokkio/workflow_repair.py"]
confidence: "high"
---

# Recorder 与 Workflow 引擎

Workflow 将成功语义执行固化为有依赖、前置条件、验证条件与版本哈希的可重放步骤；它不是无条件键鼠宏。^[src/bokkio/workflow.py#L99]

## 来源与协议

`Recorder.perform()` 捕获语义调用；`capture_receipt()` 接收已完成的原生回执，避免再次派发；`from_agent_trace()` 只固化完成且观察/决策/回执/验证一致的 trace。依赖未知 caret 的 type 会拒绝。^[src/bokkio/workflow.py#L209] ^[src/bokkio/workflow.py#L285]

`bokkio.workflow.v1` 为字面步骤协议；`v2` 加入参数和独立文件合约。输入/交付路径不混用，参数仅能进入允许的槽位。^[src/bokkio/workflow_inputs.py#L11]

## 重放与修复

`WorkflowReplay` 校验新观察、selector、预算和文件；检查点处于派发/验证未确认阶段时不能直接重复动作。修复生成带 parent hash 的新版本；模型修复只选择有限候选，不派发。^[src/bokkio/workflow.py#L332] ^[src/bokkio/workflow_repair.py#L15]

关联：[[concepts/element-identity]]、[[concepts/recovery-and-versioning]]、[[concepts/evidence-and-scoring]]。
