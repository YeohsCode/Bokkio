---
title: "DesktopAgent：阶段执行与恢复"
created: "2026-10-08"
updated: "2026-10-08"
type: "entity"
tags: ["agent", "planner", "recovery"]
sources: ["src/bokkio/agent.py", "src/bokkio/decision.py", "src/bokkio/cli.py"]
confidence: "high"
---

# DesktopAgent：阶段执行与恢复

`DesktopAgent.run()` 管理观察、阶段计划、Jev 决策、Runtime 动作、成功条件与持久化 trace。当前构造接口接受 `final_verifier` 和 `required_sources`，没有 `required_files` 参数。^[src/bokkio/agent.py#L156]

## 执行边界

- 显式应用 allowlist 与有限 action/replan/phase 预算。^[src/bokkio/agent.py#L157]
- 对当前树版本绑定决策；派发后新观察通过独立条件才能完成子任务。^[src/bokkio/decision.py#L463]
- 完成记录保留完整子任务及需求版本；恢复不会只凭复用 ID 判为已完成。^[src/bokkio/agent.py#L194]
- `final_verifier` 可阻止模型完成声明掩盖缺少交付物，并触发有界补救。^[src/bokkio/agent.py#L508]

## 文件与失败

CLI 的 `--require-file` 转换为 final verifier 回调。原生 source 获取约束与需求修订分别保留。异常触发的阶段重规划必须与 [[concepts/action-verification]] 中的未知派发规则分别核查，不能推断所有异常都能安全重试。^[src/bokkio/cli.py#L242]

关联：[[entities/planner-and-jev]]、[[concepts/recovery-and-versioning]]、[[entities/office-pilot]]。
