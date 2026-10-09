---
title: "Pending 与已知集成缺口"
created: "2026-10-08"
updated: "2026-10-09"
type: "summary"
tags: ["maintenance", "office", "vision", "safety"]
sources: ["docs/PENDING.md", "docs/evidence/2026-10-08-macos-session-recovery/readiness.json", "src/bokkio/agent.py", "src/bokkio/cli.py", "src/bokkio/office_runner.py", "tests/test_office_benchmark.py"]
confidence: "high"
---

# Pending 与已知集成缺口

当前先修实际Office任务覆盖，再扩大P7。十轮执行结果已保留，各轮0/3。构造接口不匹配已修复；会话恢复不能代替任务验收。^[docs/PENDING.md#L1]

## 队列

1. Word输入后确认：先检查实际字段/选区与保存文件，诊断未知完成，避免重复输入。
2. Excel前台/窗口拒绝：增加具体拒绝诊断，验证最新原生边界定位、范围、货币格式与保存。
3. PPT可执行候选、标题/文本/保存与阶段条件；保持置信度阈值。
4. 新工作区完整复跑固定三题，保留失败与独立产物分数。
5. 通用Planner/Jev/Workflow视觉降级，Windows截图/OCR/输入，Mac文件/进程恢复和故障验收。^[docs/PENDING.md#L5]

原始VLM、完整上游环境、真实虚拟化和跨应用职业流程仍在队列；WindowsOffice激活暂缓。主机403项通过，不代表GUI任务成功。^[docs/PENDING.md#L17]

关联：[[queries/office-pilot-readiness]]、[[entities/visual-input]]、[[entities/native-runtime]]、[[summaries/current-status]]。
