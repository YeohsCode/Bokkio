---
title: "当前阶段与证据快照"
created: "2026-10-08"
updated: "2026-10-09"
type: "summary"
tags: ["project", "evidence", "meta"]
sources: ["docs/P7-VISUAL-BRIDGE.md", "docs/PENDING.md", "docs/STATUS.md", "docs/evidence/2026-10-08-macos-session-recovery/readiness.json", "docs/evidence/2026-10-08-office-live/README.md", "docs/evidence/2026-10-08-office-pilot-ready/run.json", "docs/evidence/2026-10-08-p7-macos-runtime/validation.json", "docs/evidence/2026-10-09-office-fix/README.md", "docs/evidence/2026-10-09-visual-bridge/README.md", "src/bokkio/agent.py", "src/bokkio/office_runner.py", "src/bokkio/visual_runtime.py", "docs/evidence/2026-10-09-office-rerun/README.md"]
confidence: "high"
---

# 当前阶段与证据快照

2026-10-09快照：P6 Windows验收完成，P7部分实现与验收。主机435/435，Windows历史373/373，本轮未重跑Windows。^[docs/STATUS.md#L1]

Mac恢复fixture三轮原生动作和12次滚动通过；历史截图/OCR3/3与拒绝8/8保留为各自版本证据。Office十轮均开始三题，各轮0/3；第三轮并发与各轮源码变化已标注。^[docs/STATUS.md#L19]

最新Word派发后确认未知、Excel输入前拒绝、PPT置信度不足；本轮失败不能归因于启动时锁屏。较早OCR脚本Excel探针通过保存校验，但最新字段transport及完整Agent任务仍未通过。^[docs/evidence/2026-10-08-office-live/README.md#L20]

限定combo输入已接Office runner；通用Mac文字降级已接公共provider/Agent/Jev/CLI，真实输入与视觉Workflow、Mac文件恢复和可靠性验收待完成。Windows工作暂缓。无原始VLM或官方成绩。^[docs/PENDING.md#L5]

## 后续修复（2026-10-09）

输入拒绝与回读诊断已保留到Agent trace；同一字段最多3次回读，不重复派发。显式split button点击收窄后，真实Jev对记录的PPT快照返回click、置信度1.0（阈值0.7）。主机411/411；Mac当前锁屏，新GUI任务未开始，历史0/3仍为最新产物成绩。该决策探针没有live dispatch或Agent分数。^[docs/evidence/2026-10-09-office-fix/README.md#L1]

## Mac公共视觉接入（2026-10-09）

WindowScope/VisualObservation/VisualPolicy/VisualProvider、MacVisionProvider与HybridBackend已实现；通过显式PID/固定标题窗口接入Agent/Jev/CLI，输入标签需声明，原生可用时零OCR。恢复保留范围/策略及观察预算。^[docs/P7-VISUAL-BRIDGE.md#L5]

主机435/435；最新三次独立Mac窗口只读观察与真实Jev visual_click选择均3/3（置信度1.0），模拟Agent click/type单独验证。锁屏activation实际拒绝，未派发输入；计数文字OCR仍未验收，Office历史0/3不变。Windows工作暂缓，视觉Workflow、图标和跨窗口扩展待完成。^[docs/evidence/2026-10-09-visual-bridge/README.md#L1]

最新重跑尝试：4b6de28已推送，新工作区planned3/started0/blocked3、score=null；Mac锁屏且自动解锁失败，零题目模型调用/动作。该记录不能作为新0/3失败率，历史实际成绩不变。^[docs/evidence/2026-10-09-office-rerun/README.md#L1]

关联：[[summaries/pending-and-known-gaps]]、[[concepts/evidence-and-scoring]]、[[entities/office-pilot]]。
