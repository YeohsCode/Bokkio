---
title: "微软 Office 原题 pilot"
created: "2026-10-08"
updated: "2026-10-09"
type: "entity"
tags: ["office", "benchmark", "agent", "evidence"]
sources: ["docs/OFFICE-PILOT-READINESS.md", "docs/P7-VISUAL-BRIDGE.md", "docs/STATUS.md", "docs/evidence/2026-10-08-macos-session-recovery/readiness.json", "docs/evidence/2026-10-08-office-live/README.md", "docs/evidence/2026-10-08-office-live/scripted-transport-probe.json", "docs/evidence/2026-10-09-office-fix/README.md", "docs/evidence/2026-10-09-visual-bridge/README.md", "fixtures/windowsworld-office/manifest.json", "src/bokkio/agent.py", "src/bokkio/office_benchmark.py", "src/bokkio/office_runner.py", "src/bokkio/visual_runtime.py"]
confidence: "high"
---

# 微软 Office 原题 pilot

固定 WindowsWorld 三道 L1 原题：Word 标题/正文格式、Excel D 列货币格式、PowerPoint 标题页。原始记录、revision、许可及每题15次动作预算保留。prepare仅生成不达标输入，run使用DesktopAgent/Planner/Jev与原生backend；评分检查保存OOXML和执行开始后的保存时间。^[docs/OFFICE-PILOT-READINESS.md#L5]

## 实际执行

2026-10-08–09十轮全部启动三题，30次执行，各轮独立产物评分0/3。第三轮有并发fixture干扰，各轮代码变化，属于开发诊断。最新Word输入后确认未知，Excel输入前窗口/前台拒绝，PPT置信度不足；Agent均blocked，run的completed仅表示执行循环返回。^[docs/evidence/2026-10-08-office-live/README.md#L3]

独立Excel脚本探针用较早OCR定位完成两次字段替换及保存校验，agent_score=false。最新原生边界定位transport和完整Agent任务仍待通过；原始VLM未执行，无官方成绩。^[docs/evidence/2026-10-08-office-live/scripted-transport-probe.json#L1]

## 已修复与下一步

executor改final_verifier；补充真实AXConfirm、同名窗口身份、真实前台激活、只读选区和弹窗阶段规划。限定字段transport已接Office runner；通用Mac文字OCR降级已实现，实际输入与Office成绩仍待验收。先诊断三类失败再完整复跑。^[docs/STATUS.md#L19]

## 后续修复（2026-10-09）

输入拒绝与回读诊断已保留到Agent trace；同一字段最多3次回读，不重复派发。显式split button点击收窄后，真实Jev对记录的PPT快照返回click、置信度1.0（阈值0.7）。主机411/411；Mac当前锁屏，新GUI任务未开始，历史0/3仍为最新产物成绩。该决策探针没有live dispatch或Agent分数。^[docs/evidence/2026-10-09-office-fix/README.md#L1]

## Mac公共视觉接入（2026-10-09）

WindowScope/VisualObservation/VisualPolicy/VisualProvider、MacVisionProvider与HybridBackend已实现；通过显式PID/固定标题窗口接入Agent/Jev/CLI，输入标签需声明，原生可用时零OCR。恢复保留范围/策略及观察预算。^[docs/P7-VISUAL-BRIDGE.md#L5]

主机435/435；最新三次独立Mac窗口只读观察与真实Jev visual_click选择均3/3（置信度1.0），模拟Agent click/type单独验证。锁屏activation实际拒绝，未派发输入；计数文字OCR仍未验收，Office历史0/3不变。Windows工作暂缓，视觉Workflow、图标和跨窗口扩展待完成。^[docs/evidence/2026-10-09-visual-bridge/README.md#L1]

关联：[[queries/office-pilot-readiness]]、[[concepts/evidence-and-scoring]]、[[summaries/pending-and-known-gaps]]。
