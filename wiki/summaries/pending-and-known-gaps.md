---
title: "Pending 与已知集成缺口"
created: "2026-10-08"
updated: "2026-10-09"
type: "summary"
tags: ["maintenance", "office", "vision", "safety"]
sources: ["docs/P7-VISUAL-BRIDGE.md", "docs/PENDING.md", "docs/evidence/2026-10-08-macos-session-recovery/readiness.json", "docs/evidence/2026-10-09-office-fix/README.md", "docs/evidence/2026-10-09-visual-bridge/README.md", "src/bokkio/agent.py", "src/bokkio/cli.py", "src/bokkio/office_runner.py", "src/bokkio/visual_runtime.py", "tests/test_office_benchmark.py"]
confidence: "high"
---

# Pending 与已知集成缺口

当前先修实际Office任务覆盖，再扩大P7。十轮执行结果已保留，各轮0/3。构造接口不匹配已修复；会话恢复不能代替任务验收。^[docs/PENDING.md#L1]

## 队列

1. Word输入后确认：先检查实际字段/选区与保存文件，诊断未知完成，避免重复输入。
2. Excel前台/窗口拒绝：增加具体拒绝诊断，验证最新原生边界定位、范围、货币格式与保存。
3. PPT可执行候选、标题/文本/保存与阶段条件；保持置信度阈值。
4. 新工作区完整复跑固定三题，保留失败与独立产物分数。
5. Mac公共OCR与Agent/Jev/CLI文字降级已实现；继续真实输入、视觉Workflow、Mac文件/进程恢复和故障验收，Windows工作暂缓。^[docs/PENDING.md#L5]

原始VLM、完整上游环境、真实虚拟化和跨应用职业流程仍在队列；WindowsOffice激活暂缓。主机411项通过，不代表GUI任务成功。^[docs/PENDING.md#L17]

## 后续修复（2026-10-09）

输入拒绝与回读诊断已保留到Agent trace；同一字段最多3次回读，不重复派发。显式split button点击收窄后，真实Jev对记录的PPT快照返回click、置信度1.0（阈值0.7）。主机411/411；Mac当前锁屏，新GUI任务未开始，历史0/3仍为最新产物成绩。该决策探针没有live dispatch或Agent分数。^[docs/evidence/2026-10-09-office-fix/README.md#L1]

## Mac公共视觉接入（2026-10-09）

WindowScope/VisualObservation/VisualPolicy/VisualProvider、MacVisionProvider与HybridBackend已实现；通过显式PID/固定标题窗口接入Agent/Jev/CLI，输入标签需声明，原生可用时零OCR。恢复保留范围/策略及观察预算。^[docs/P7-VISUAL-BRIDGE.md#L5]

主机435/435；最新三次独立Mac窗口只读观察与真实Jev visual_click选择均3/3（置信度1.0），模拟Agent click/type单独验证。锁屏activation实际拒绝，未派发输入；计数文字OCR仍未验收，Office历史0/3不变。Windows工作暂缓，视觉Workflow、图标和跨窗口扩展待完成。^[docs/evidence/2026-10-09-visual-bridge/README.md#L1]

关联：[[queries/office-pilot-readiness]]、[[entities/visual-input]]、[[entities/native-runtime]]、[[summaries/current-status]]。
