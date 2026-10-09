---
title: "微软 Office 原题 pilot"
created: "2026-10-08"
updated: "2026-10-09"
type: "entity"
tags: ["office", "benchmark", "agent", "evidence"]
sources: ["docs/OFFICE-PILOT-READINESS.md", "docs/STATUS.md", "docs/evidence/2026-10-08-macos-session-recovery/readiness.json", "docs/evidence/2026-10-08-office-live/README.md", "docs/evidence/2026-10-08-office-live/scripted-transport-probe.json", "fixtures/windowsworld-office/manifest.json", "src/bokkio/agent.py", "src/bokkio/office_benchmark.py", "src/bokkio/office_runner.py"]
confidence: "high"
---

# 微软 Office 原题 pilot

固定 WindowsWorld 三道 L1 原题：Word 标题/正文格式、Excel D 列货币格式、PowerPoint 标题页。原始记录、revision、许可及每题15次动作预算保留。prepare仅生成不达标输入，run使用DesktopAgent/Planner/Jev与原生backend；评分检查保存OOXML和执行开始后的保存时间。^[docs/OFFICE-PILOT-READINESS.md#L5]

## 实际执行

2026-10-08–09十轮全部启动三题，30次执行，各轮独立产物评分0/3。第三轮有并发fixture干扰，各轮代码变化，属于开发诊断。最新Word输入后确认未知，Excel输入前窗口/前台拒绝，PPT置信度不足；Agent均blocked，run的completed仅表示执行循环返回。^[docs/evidence/2026-10-08-office-live/README.md#L3]

独立Excel脚本探针用较早OCR定位完成两次字段替换及保存校验，agent_score=false。最新原生边界定位transport和完整Agent任务仍待通过；原始VLM未执行，无官方成绩。^[docs/evidence/2026-10-08-office-live/scripted-transport-probe.json#L1]

## 已修复与下一步

executor改final_verifier；补充真实AXConfirm、同名窗口身份、真实前台激活、只读选区和弹窗阶段规划。限定字段transport已接Office runner，通用自动视觉降级待实现。先诊断三类失败再完整复跑。^[docs/STATUS.md#L19]

关联：[[queries/office-pilot-readiness]]、[[concepts/evidence-and-scoring]]、[[summaries/pending-and-known-gaps]]。
